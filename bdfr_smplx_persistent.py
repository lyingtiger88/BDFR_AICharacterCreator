"""Maya-side persistent SMPL-X controller, nonblocking Qt QProcess, latest-only requests."""
import base64
import json
import math
import struct
from pathlib import Path

try:
    from PySide6 import QtCore
except ImportError:
    from PySide2 import QtCore

class PersistentController(QtCore.QObject):
    def __init__(self, window_name, settings):
        super(PersistentController,self).__init__()
        self.window_name=window_name
        self.settings=settings
        self.process=None
        self.stdout=bytearray()
        self.pending=False
        self.inflight=False
        self.revision=0
        self.sent_revision=0
        self.last_error=None
        self.timer=QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(90)
        self.timer.timeout.connect(self._send)
        self.engine_key=None
        self.request_id=0
        self.closed=False
        self.active_request_id=None
        self.sent_details=(0.0,0.0,0.0)

    def schedule(self):
        if self.closed:return
        self.revision+=1
        self.pending=True
        self.timer.start()

    def _ensure_engine(self, data):
        import maya.cmds as cmds
        from bdfr_smplx_maya import ROOT
        key=(data["python"],data["models"])
        if self.process and self.process.state()!=QtCore.QProcess.NotRunning:
            if key!=self.engine_key:
                self.process.kill()
                self.process.waitForFinished(1000)
                self.process.deleteLater()
                self.process=None
                self.inflight=False
                self.stdout.clear()
            else:
                return True
        if not Path(key[0]).is_file() or not Path(key[1]).is_dir():
            cmds.warning("[BDFR] Python or SMPL-X weights folder not found")
            return False
        proc=QtCore.QProcess(self)
        proc.setProgram(key[0])
        proc.setArguments(["-u",str(ROOT/"smplx_server.py"),"--models",key[1]])
        proc.setProcessChannelMode(QtCore.QProcess.SeparateChannels)
        proc.readyReadStandardOutput.connect(self._received)
        proc.readyReadStandardError.connect(self._stderr)
        proc.finished.connect(self._stopped)
        proc.start()
        self.process=proc
        self.engine_key=key
        return True

    def _send(self):
        import maya.cmds as cmds
        if not cmds.window(self.window_name,exists=True) or not self.pending or self.inflight:
            return
        data=self.settings()
        if not self._ensure_engine(data):
            return
        body=[0.0]*63
        body[15*3+2]=math.radians(data["shoulder"])
        body[16*3+2]=-math.radians(data["shoulder"])
        body[17*3+1]=math.radians(data["elbow"])
        body[18*3+1]=-math.radians(data["elbow"])
        hand=[0.0]*45
        for i in range(0,45,3):
            hand[i]=math.radians(data["hand"])
        self.request_id+=1
        request={"cmd":"evaluate","id":self.request_id,"gender":data["gender"],
                 "betas":data["betas"],"body_pose":body,"left_hand":hand,
                 "right_hand":hand,"expression":[data["expression"]]}
        payload=(json.dumps(request,separators=(",",":"))+"\n").encode("utf-8")
        self.process.write(payload)
        self.sent_details=(data.get("breast_size",0.0),data.get("hip_width",0.0),data.get("glute_size",0.0))
        self.sent_revision=self.revision
        self.active_request_id=self.request_id
        self.pending=False
        self.inflight=True

    def _received(self):
        if self.closed or not self.process:return
        self.stdout.extend(bytes(self.process.readAllStandardOutput()))
        while b"\n" in self.stdout:
            line,_,rest=self.stdout.partition(b"\n")
            self.stdout=bytearray(rest)
            try:
                result=json.loads(line.decode("utf-8"))
                self.inflight=False
                if result.get("id")!=self.active_request_id:
                    raise ValueError("Unexpected SMPL-X response ID")
                if not result.get("ok"):
                    raise RuntimeError(result.get("error","Unknown engine error"))
                if self.sent_revision==self.revision and not self.pending:
                    self._apply(result)
                else:
                    self.pending=True
            except Exception as exc:
                self.inflight=False
                self.last_error=str(exc)
                import maya.cmds as cmds
                cmds.warning("[BDFR persistent] "+str(exc)[:450])
            if self.pending:self.timer.start(0)

    def _apply(self, result):
        import maya.cmds as cmds
        from maya.api import OpenMaya as om
        from bdfr_smplx_editor import TARGET, STATE, _shape
        vertices=base64.b64decode(result["vertices"])
        faces_raw=base64.b64decode(result["faces"])
        n=result["vertex_count"]
        face_count=result["face_count"]
        if n!=10475 or len(vertices)!=n*12 or len(faces_raw)!=face_count*12:
            raise ValueError("Unexpected SMPL-X geometry buffer dimensions")
        floats=struct.unpack("<"+"f"*(n*3),vertices)
        from bdfr_body_details import deform
        raw_points=((floats[i],floats[i+1],floats[i+2]) for i in range(0,n*3,3))
        raw_points=list(raw_points)
        detailed=deform(raw_points,*self.sent_details)
        max_delta=max((math.dist(a,b) for a,b in zip(raw_points,detailed)),default=0.0)
        print("[BDFR Details] breast={:.2f}, hips={:.2f}, glutes={:.2f}, max displacement={:.1f} mm".format(
            *self.sent_details,max_delta*1000))
        points=[om.MPoint(*xyz) for xyz in detailed]
        gender=result["gender"]
        if cmds.objExists(TARGET) and STATE.get("gender") not in (None,gender):
            cmds.delete(TARGET)
            STATE["gender"]=None
        if cmds.objExists(TARGET):
            fn=_shape(TARGET)
            if fn.numVertices!=n: raise ValueError("Topology mismatch")
            fn.setPoints(points,om.MSpace.kObject)
            transform=TARGET
        else:
            ids=struct.unpack("<"+"i"*(face_count*3),faces_raw)
            obj=om.MFnMesh().create(points,[3]*face_count,list(ids))
            dag=om.MFnDagNode(obj)
            transform=cmds.rename(om.MFnDagNode(dag.parent(0)).fullPathName(),TARGET)
            cmds.setAttr(transform+".scale",100,100,100,type="double3")
        # Keep scale 100 in centimetre Maya scene; position lowest Y exactly at ground.
        bbox=cmds.exactWorldBoundingBox(transform)
        cmds.move(0,-bbox[1],0,transform,relative=True,worldSpace=True)
        STATE["gender"]=gender
        self.last_error=None
        print("[BDFR] SMPL-X engine: {} ms, {} verts".format(result["compute_ms"],n))

    def _stderr(self):
        if self.process:
            error=bytes(self.process.readAllStandardError()).decode("utf-8","replace")
            if error.strip():print("[BDFR SMPL-X stderr]",error[-1500:])

    def _stopped(self,*_):
        if self.closed:return
        self.inflight=False
        self.process=None
        if self.pending:self.timer.start(100)

    def close(self):
        self.closed=True
        self.pending=False
        self.timer.stop()
        if self.process and self.process.state()!=QtCore.QProcess.NotRunning:
            self.process.kill()
        self.process=None

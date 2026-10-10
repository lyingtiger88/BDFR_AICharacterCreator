"""Non-blocking SMPL-X live preview for Maya.
Evaluates in external Python via Qt QProcess and updates Maya only on the UI thread.
Only the latest slider state is applied; drag changes are debounced.
"""
from pathlib import Path
from math import radians

try:
    from PySide6 import QtCore
except ImportError:
    from PySide2 import QtCore

class LiveController(QtCore.QObject):
    def __init__(self, window_name, settings):
        super(LiveController, self).__init__()
        self.window_name=window_name
        self.settings=settings
        self.timer=QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self._start)
        self.process=None
        self.dirty=False
        self.requested_gender=None
        self.running_revision=-1
        self.revision=0
        self.last_error=None

    def schedule(self):
        self.revision+=1
        self.dirty=True
        self.timer.start()

    def _start(self):
        if self.process is not None:
            return  # Wait for running process; coalesce intermediate changes.
        if not self.dirty:
            return
        import maya.cmds as cmds
        from bdfr_smplx_maya import ROOT, OUTPUT
        if not cmds.window(self.window_name,exists=True):
            return
        data=self.settings()
        py=Path(data["python"])
        weights=Path(data["models"])
        if not py.is_file() or not weights.is_dir():
            cmds.warning("[BDFR Live] Configure Python and SMPL-X model weights.")
            return
        g=data["gender"]
        body=[0.0]*63
        body[15*3+2]=radians(data["shoulder"])
        body[16*3+2]=-radians(data["shoulder"])
        body[17*3+1]=radians(data["elbow"])
        body[18*3+1]=-radians(data["elbow"])
        hands=[0.0]*45
        for i in range(0,45,3):
            hands[i]=radians(data["hand"])
        expression=[data["expression"]]+[0.0]*9
        params=["--models",str(weights),"--out",str(OUTPUT),"--gender",g,
                "--betas"]+[str(v) for v in data["betas"]]
        for flag,seq in (("--body-pose",body),("--left-hand",hands),
                         ("--right-hand",hands),("--expression",expression)):
            params.append(flag)
            params.extend(str(v) for v in seq)
        OUTPUT.parent.mkdir(parents=True,exist_ok=True)
        self.process=QtCore.QProcess(self)
        self.process.setProgram(str(py))
        self.process.setArguments([str(ROOT/"smplx_export.py")]+params)
        self.process.setProcessChannelMode(QtCore.QProcess.SeparateChannels)
        self.running_revision=self.revision
        self.requested_gender=g
        self.dirty=False
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._errored)
        self.process.start()

    def _errored(self, error):
        # Finished generally fires for running processes; startup failure may not.
        if self.process and self.process.state()==QtCore.QProcess.NotRunning:
            self._finalize(False,"Unable to start external Python: "+str(error))

    def _finished(self, code, status):
        if self.process is None:
            return
        details=bytes(self.process.readAllStandardError()).decode("utf-8","replace")[-1500:]
        ok=(code==0 and status==QtCore.QProcess.NormalExit)
        self._finalize(ok,details)

    def _finalize(self, ok, details):
        proc=self.process
        if proc is None:
            return
        self.process=None
        proc.deleteLater()
        # Ignore stale results and apply only latest slider state.
        if self.running_revision!=self.revision or self.dirty:
            self.dirty=True
            self.timer.start()
            return
        if ok:
            try:
                from bdfr_smplx_editor import apply_exported, STATE, TARGET
                import maya.cmds as cmds
                if not cmds.window(self.window_name,exists=True):
                    return
                if cmds.objExists(TARGET) and STATE.get("gender") not in (None,self.requested_gender):
                    # Gender switch recreates target to preserve material/topology assumptions.
                    cmds.delete(TARGET)
                    STATE["gender"]=None
                apply_exported(self.requested_gender)
                print("[BDFR Live] Updated SMPL-X:",self.requested_gender)
                self.last_error=None
            except Exception as exc:
                self.last_error=str(exc)
                import maya.cmds as cmds
                cmds.warning("[BDFR Live] Could not update mesh: "+str(exc))
        else:
            self.last_error=details or "SMPL-X process failed"
            import maya.cmds as cmds
            cmds.warning("[BDFR Live] "+self.last_error[-400:])

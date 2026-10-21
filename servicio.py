"""Entrypoint del .exe: ejecuta el worker como servicio de Windows (pywin32).

    worker.exe --startup auto install   registra el servicio (una vez, como Administrador)
    worker.exe start | stop | remove    lo inicia, detiene o elimina
    worker.exe debug                    lo corre en consola como si fuera el servicio
    worker.exe                          lanzado por Windows corre como servicio;
                                        con doble clic corre el worker en consola

worker se importa recien al arrancar el servicio porque config carga el .env y el logging:
asi install/remove funcionan aunque falte el .env."""
import os
import sys

import pywintypes
import servicemanager
import win32service
import win32serviceutil
import winerror


class SagiWorkerService(win32serviceutil.ServiceFramework):
    _svc_name_ = "SAGIWorker"
    _svc_display_name_ = "SAGI Worker"
    _svc_description_ = "Lee el log de PowerCurve (InterceptPwc26201) y carga cada solicitud en Snowflake."

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING, waitHint=60000)
        import worker
        worker.detener.set()

    def SvcDoRun(self):
        try:
            import worker
            worker.main()
        except BaseException as exc:  # incluye el sys.exit de config.py si falta el .env
            servicemanager.LogErrorMsg(f"SAGIWorker termino por un error: {exc!r}")
            # Salir sin reportar SERVICE_STOPPED: Windows lo toma como caida y aplica la
            # recuperacion configurada (reiniciar el servicio).
            os._exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        win32serviceutil.HandleCommandLine(SagiWorkerService)
    else:
        try:
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(SagiWorkerService)
            servicemanager.StartServiceCtrlDispatcher()
        except pywintypes.error as exc:
            if exc.winerror != winerror.ERROR_FAILED_SERVICE_CONTROLLER_CONNECT:
                raise
            # No lo lanzo Windows como servicio (doble clic o consola): worker normal.
            import worker
            worker.main()

"""Bounded capture processes, optionally on an invisible Windows desktop.

Godot's headless display driver only supports dummy rendering.  An isolated
desktop keeps the normal Windows/Vulkan renderer without placing a window on
the user's input desktop.  This module never activates or switches desktops.
"""
import ctypes
from ctypes import wintypes
import os
import subprocess
import uuid


def run_capture(command, stream, timeout, background=False):
    if not background:
        with subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT) as process:
            try:
                return process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
                raise
    if os.name != 'nt':
        raise RuntimeError('--background requires Windows isolated desktop support')
    return _run_on_desktop(command, stream, timeout)


def _run_on_desktop(command, stream, timeout):
    import msvcrt

    class STARTUPINFO(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('lpReserved', wintypes.LPWSTR),
                    ('lpDesktop', wintypes.LPWSTR), ('lpTitle', wintypes.LPWSTR),
                    ('dwX', wintypes.DWORD), ('dwY', wintypes.DWORD),
                    ('dwXSize', wintypes.DWORD), ('dwYSize', wintypes.DWORD),
                    ('dwXCountChars', wintypes.DWORD), ('dwYCountChars', wintypes.DWORD),
                    ('dwFillAttribute', wintypes.DWORD), ('dwFlags', wintypes.DWORD),
                    ('wShowWindow', wintypes.WORD), ('cbReserved2', wintypes.WORD),
                    ('lpReserved2', ctypes.POINTER(ctypes.c_byte)),
                    ('hStdInput', wintypes.HANDLE), ('hStdOutput', wintypes.HANDLE),
                    ('hStdError', wintypes.HANDLE)]

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [('hProcess', wintypes.HANDLE), ('hThread', wintypes.HANDLE),
                    ('dwProcessId', wintypes.DWORD), ('dwThreadId', wintypes.DWORD)]

    user32 = ctypes.WinDLL('user32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    user32.CreateDesktopW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p,
                                      wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
    user32.CreateDesktopW.restype = wintypes.HANDLE
    user32.CloseDesktop.argtypes = [wintypes.HANDLE]
    user32.CloseDesktop.restype = wintypes.BOOL
    kernel32.CreateProcessW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR,
        ctypes.c_void_p, ctypes.c_void_p, wintypes.BOOL, wintypes.DWORD,
        ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(STARTUPINFO),
        ctypes.POINTER(PROCESS_INFORMATION)]
    kernel32.CreateProcessW.restype = wintypes.BOOL
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateProcess.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    name = 'ManilaCapture_' + uuid.uuid4().hex
    # Read/write objects, create windows/menus, enumerate. No switch permission.
    desktop = user32.CreateDesktopW(name, None, None, 0, 0x00C7, None)
    if not desktop:
        raise ctypes.WinError(ctypes.get_last_error())
    info = PROCESS_INFORMATION()
    try:
        with open(os.devnull, 'rb') as input_stream:
            handles = [msvcrt.get_osfhandle(input_stream.fileno()),
                       msvcrt.get_osfhandle(stream.fileno())]
            inherited = [os.get_handle_inheritable(handle) for handle in handles]
            try:
                for handle in handles:
                    os.set_handle_inheritable(handle, True)
                startup = STARTUPINFO()
                startup.cb = ctypes.sizeof(startup)
                startup.lpDesktop = name
                startup.dwFlags = 0x00000100  # STARTF_USESTDHANDLES
                startup.hStdInput, startup.hStdOutput = handles
                startup.hStdError = handles[1]
                cmdline = ctypes.create_unicode_buffer(subprocess.list2cmdline(command))
                # No console window; graphical windows belong only to our desktop.
                if not kernel32.CreateProcessW(None, cmdline, None, None, True,
                        0x08000000, None, None, ctypes.byref(startup), ctypes.byref(info)):
                    raise ctypes.WinError(ctypes.get_last_error())
            finally:
                for handle, value in zip(handles, inherited):
                    os.set_handle_inheritable(handle, value)
        kernel32.CloseHandle(info.hThread)
        info.hThread = None
        print('BACKGROUND_CAPTURE_PID', info.dwProcessId, 'DESKTOP', name, flush=True)
        wait = kernel32.WaitForSingleObject(info.hProcess, int(timeout * 1000))
        if wait == 0x00000102:  # WAIT_TIMEOUT
            kernel32.TerminateProcess(info.hProcess, 1)
            kernel32.WaitForSingleObject(info.hProcess, 10000)
            raise subprocess.TimeoutExpired(command, timeout)
        if wait != 0:
            raise ctypes.WinError(ctypes.get_last_error())
        code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(code)):
            raise ctypes.WinError(ctypes.get_last_error())
        return code.value
    finally:
        if info.hThread:
            kernel32.CloseHandle(info.hThread)
        if info.hProcess:
            # Also bound the child if this wrapper is interrupted or a wait fails.
            if kernel32.WaitForSingleObject(info.hProcess, 0) == 0x00000102:
                kernel32.TerminateProcess(info.hProcess, 1)
                kernel32.WaitForSingleObject(info.hProcess, 10000)
            kernel32.CloseHandle(info.hProcess)
        user32.CloseDesktop(desktop)

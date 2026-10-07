import os
import subprocess
import sys


def _terminate_stale_project_bots() -> None:
    import psutil
    script_names = ["bot_mixed.py", "bot_single.py", "run_two_bots.py"]
    current_pid = os.getpid()
    parent_pid = os.getppid()

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                pid = proc.info['pid']
                if pid == current_pid or pid == parent_pid:
                    continue
                cmdline = proc.info.get('cmdline') or []
                if any(script_name in cmd for cmd in cmdline for script_name in script_names):
                    print(f"Terminating stale process {pid}: {' '.join(cmdline)}")
                    proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass


def main() -> None:
    _terminate_stale_project_bots()

    env = os.environ.copy()
    mixed_token = env.get("TELEGRAM_BOT_TOKEN_MIXED") or "8994284779:AAFbankKA7pdIZ8COERHm4e_5XRhZZhuLc4"
    single_token = env.get("TELEGRAM_BOT_TOKEN_SINGLE") or "8984819329:AAE_3cLiainaEXaEswueYBcly7Rj4PYq0U8"

    env["TELEGRAM_BOT_TOKEN_MIXED"] = mixed_token
    env["TELEGRAM_BOT_TOKEN_SINGLE"] = single_token

    if not mixed_token and not single_token:
        raise RuntimeError(
            "Set TELEGRAM_BOT_TOKEN_MIXED and/or TELEGRAM_BOT_TOKEN_SINGLE before running this launcher."
        )

    processes = []
    if mixed_token:
        print("Starting mixed bot...")
        processes.append(subprocess.Popen([sys.executable, "bot_mixed.py"], env=env))
    if single_token:
        print("Starting single bot...")
        processes.append(subprocess.Popen([sys.executable, "bot_single.py"], env=env))

    try:
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        for process in processes:
            process.terminate()
        for process in processes:
            process.wait()


if __name__ == "__main__":
    main()

import os
import subprocess
import sys


def _terminate_stale_project_bots() -> None:
    script_names = ["bot_mixed.py", "bot_single.py", "run_two_bots.py"]
    script_filter = " | ".join(f"$_.CommandLine -match '{name}'" for name in script_names)
    command = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -eq 'python.exe' -and ("
        f"{script_filter}"
        ") } | "
        "ForEach-Object { $_.Terminate() }"
    )
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", command], check=False)
    except FileNotFoundError:
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

"""Uruchamia graficzną wersję EvidLock Light."""

from evidlock_light.app import main
from evidlock_light.single_instance import SingleInstance, activate_existing_window


if __name__ == "__main__":
    instance = SingleInstance()
    if not instance.acquired:
        activate_existing_window()
        raise SystemExit(0)
    try:
        main()
    finally:
        instance.release()

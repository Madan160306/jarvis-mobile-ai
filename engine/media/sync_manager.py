"""
SyncManager: Synchronizes volume across PC and mobile simultaneously.
"""
from engine.device.android_controller import AndroidController
from engine.device.device_controller import DeviceController


class SyncManager:

    @classmethod
    def sync_volume(cls, level: int) -> str:
        """
        Set PC to exactly `level` percent.
        Set mobile by pressing volume keys proportionally.
        """
        level = max(0, min(100, level))
        results = []

        # PC Volume (exact)
        pc_msg = DeviceController.set_volume(level)
        results.append(f"PC: {pc_msg}")

        # Mobile: press volume-up key (level // 7) times, 
        # volume-down (15 - level // 7) times to normalise first then adjust.
        # Simpler: reset to 0 then go up.
        for _ in range(15):  # reset by pressing volume down 15 times
            AndroidController.change_volume_once("down")

        steps_up = max(0, level // 7)
        for _ in range(steps_up):
            AndroidController.change_volume_once("up")

        results.append(f"Mobile: volume synced to ~{level}%")

        return " | ".join(results)

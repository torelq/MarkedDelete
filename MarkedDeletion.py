from gi.repository import Nautilus, GObject, Gio, GLib
from typing import List
import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class MarkedDeletionMenuProvider(GObject.GObject, Nautilus.MenuProvider):

    def __init__(self):
        super().__init__()

    def on_activate(
        self,
        menu: Nautilus.MenuItem,
        files: List[Nautilus.FileInfo],
    ) -> None:

        for file_info in files:
            self.delete_and_mark(file_info)

    def delete_and_mark(self, file_info: Nautilus.FileInfo) -> None:
        file = file_info.get_location()

        parent = file.get_parent()
        if parent is None:
            logger.warning(
                "Cannot determine parent directory for %s",
                file.get_uri(),
            )
            return

        marker_name = file.get_basename() + ".DELETED"
        marker = parent.get_child(marker_name)

        cancellable = Gio.Cancellable()

        try:
            stream = marker.create(
                Gio.FileCreateFlags.NONE,
                cancellable,
            )
            stream.close(cancellable)

        except GLib.Error as e:
            if e.matches(
                Gio.io_error_quark(),
                Gio.IOErrorEnum.EXISTS,
            ):
                logger.info(
                    "Marker already exists, skipping: %s",
                    file.get_uri(),
                )
            else:
                logger.warning(
                    "Could not create marker %s: %s",
                    marker.get_uri(),
                    e,
                )


        # We created this marker, so we're responsible for it.
        try:
            file.trash(cancellable)

        except GLib.Error as e:
            logger.warning(
                "Could not move %s to Trash: %s",
                file.get_uri(),
                e,
            )

            try:
                marker.delete(cancellable)
            except GLib.Error as cleanup_error:
                logger.error(
                    "Could not remove marker %s: %s",
                    marker.get_uri(),
                    cleanup_error,
                )

            return

        logger.info(
            "Moved %s to Trash and created %s",
            file.get_uri(),
            marker.get_uri(),
        )

    def get_file_items(
        self,
        files: List[Nautilus.FileInfo],
    ) -> List[Nautilus.MenuItem]:
        
        if any(file.get_uri().startswith("trash://") for file in files):
            return []

        item = Nautilus.MenuItem(
            name="MarkedDeletionExtension::Delete_And_Mark",
            label="Delete and Mark",
        )

        item.connect("activate", self.on_activate, files)

        return [item]

    # Empty function to prevent a Nautilus warning.
    def get_background_items(
        self,
        current_folder: Nautilus.FileInfo,
    ) -> List[Nautilus.MenuItem]:
        return []
"""Keep tests isolated from the live display and user configuration."""

import os
import tempfile
import pytest


_TEST_CONFIG = tempfile.TemporaryDirectory(prefix="night-light-by-ht-tests-")
os.environ["NIGHT_LIGHT_BY_HT_DISABLE_DISPLAY_BACKEND"] = "1"
os.environ["NIGHT_LIGHT_BY_HT_CONFIG_DIR"] = _TEST_CONFIG.name


@pytest.fixture(scope='session')
def _tk_session():
    """One Tcl interpreter/GUI owner, as in the resident app.

    Recreating Tk after the layout module intermittently failed loading Tcl
    resources in this Windows/Python runtime. Keep all UI assertions but use
    Toplevels on one owner; do not catch/skip construction failures or retry.
    Fresh-process installation/startup tests remain a separate release gate.
    """
    import customtkinter as ctk
    ctk.deactivate_automatic_dpi_awareness()
    root=ctk.CTk()
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def tk_root(_tk_session):
    import gc
    import customtkinter as ctk
    ctk.set_widget_scaling(1)
    ctk.set_window_scaling(1)
    yield _tk_session
    ctk.set_widget_scaling(1)
    ctk.set_window_scaling(1)
    # Destroyed CTk widgets/fonts can remain in cycles. Finalize them on their
    # Tcl owner now, not during a later JSON allocation on a settings worker
    # while the test owner is synchronously waiting for that worker barrier.
    gc.collect()

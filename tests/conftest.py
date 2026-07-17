import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    # pytest-homeassistant-custom-component blocks custom_components from
    # loading during tests unless this fixture is pulled in - required for
    # every test file in this suite.
    yield

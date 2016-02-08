import os, sys
BASE_TEMPLATES_DIR = os.path.dirname(os.path.abspath(__file__)) + '/templates'

@app.context_processor
def select_parent_template():
    """Check if it's ajax, if so no need any parent template."""
    parent_template = "dummy_parent.html" if request.is_xhr else "base.html"
    return {'parent_template': parent_template}


@app.context_processor
def openshift():
    """Check if it's openshift."""
    return {'OPENSHIFT': ('OPENSHIFT_APP_NAME' in os.environ)}

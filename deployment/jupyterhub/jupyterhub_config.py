# Betabox JupyterHub configuration

c = get_config()  # noqa

c.JupyterHub.bind_url = "http://:8000"
c.JupyterHub.cookie_secret_file = "/opt/jupyterhub/jupyterhub_cookie_secret"
c.JupyterHub.db_url = "sqlite:////opt/jupyterhub/jupyterhub.sqlite"

c.JupyterHub.template_paths = ["/opt/jupyterhub/theme/templates"]

c.Authenticator.allow_all = True
c.Authenticator.admin_users = {"pi"}

c.Spawner.cmd = ["/opt/jupyterhub/venv/bin/jupyterhub-singleuser"]
c.Spawner.default_url = "/lab"
c.Spawner.notebook_dir = "~"

c.Spawner.environment = {
    "JUPYTER_PATH": "/opt/jupyterhub/venv/share/jupyter",
}

c.JupyterHub.services = [
    {
        "name": "idle-culler",
        "admin": True,
        "command": [
            "/opt/jupyterhub/venv/bin/python",
            "-m",
            "jupyterhub_idle_culler",
            "--timeout=600",
            "--cull-every=60",
        ],
    }
]

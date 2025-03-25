from requests import get as http_get
from sqlalchemy import ForeignKey, Integer
from warnings import warn

try:
    from pynetbox import api as netbox_api
except ImportError as exc:
    warn(f"Couldn't import pynetbox module ({exc})")

from eNMS.database import db
from eNMS.environment import env
from eNMS.fields import HiddenField, PasswordField, SelectField, StringField
from eNMS.forms import ServiceForm
from eNMS.models.automation import Service


class TopologyImportService(Service):
    __tablename__ = "topology_import_service"
    pretty_name = "Topology Import"
    id = db.Column(Integer, ForeignKey("service.id"), primary_key=True)
    netbox_address = db.Column(db.SmallString)
    netbox_token = db.Column(db.SmallString)
    opennms_address = db.Column(db.SmallString)
    opennms_devices = db.Column(db.SmallString)
    opennms_login = db.Column(db.SmallString)
    opennms_password = db.Column(db.SmallString)
    librenms_address = db.Column(db.SmallString)
    librenms_token = db.Column(db.SmallString)

    import_type = db.Column(db.SmallString)

    __mapper_args__ = {"polymorphic_identity": "topology_import_service"}

    def job(self, run):
        getattr(self, f"query_{self.import_type}")()
        return {"success": True}
        
    def query_netbox(self):
        import requests
        session = requests.Session()
        session.verify = False
        nb = netbox_api(self.netbox_address, env.get_password(self.netbox_token))
        nb.http_session = session
        for device in nb.dcim.devices.all():
            device_ip = device.primary_ip4 or device.primary_ip6
            name = f"{device.name} ({device_ip})"
            
            # Check if the node with the same name already exists
            existing_node = db.session.query(Node).filter_by(name=name).first()
            
            if existing_node:
                # If the node exists, update its position and coordinates
                existing_node.positions = device.position
                existing_node.latitude = str(nb.dcim.sites.get(name=device.site).latitude)
                existing_node.longitude = str(nb.dcim.sites.get(name=device.site).longitude)
            else:
                db.factory(
                    "node",
                    **{
                        "name": name,
                        "positions": device.position,
                        "latitude": str(nb.dcim.sites.get(name=device.site).latitude),
                        "longitude": str(nb.dcim.sites.get(name=device.site).longitude),
                    },
                )

    def query_opennms(self):
        json_devices = http_get(
            self.opennms_devices,
            headers={"Accept": "application/json"},
            auth=(self.opennms_login, env.get_password(self.opennms_password)),
        ).json()["node"]
        devices = {
            device["id"]: {
                "name": device.get("label", device["id"]),
                "description": device["assetRecord"].get("description", ""),
                "location": device["assetRecord"].get("building", ""),
                "vendor": device["assetRecord"].get("manufacturer", ""),
                "model": device["assetRecord"].get("modelNumber", ""),
                "operating_system": device.get("operatingSystem", ""),
                "os_version": device["assetRecord"].get("sysDescription", ""),
                "longitude": device["assetRecord"].get("longitude", 0.0),
                "latitude": device["assetRecord"].get("latitude", 0.0),
            }
            for device in json_devices
        }
        for device in list(devices):
            link = http_get(
                f"{self.opennms_address}/nodes/{device}/ipinterfaces",
                headers={"Accept": "application/json"},
                auth=(self.opennms_login, env.get_password(self.opennms_password)),
            ).json()
            for interface in link["ipInterface"]:
                if interface["snmpPrimary"] == "P":
                    devices[device]["ip_address"] = interface["ipAddress"]
                    db.factory("device", **devices[device])

    def query_librenms(self):
        devices = http_get(
            f"{self.librenms_address}/api/v0/devices",
            headers={"X-Auth-Token": env.get_password(self.librenms_token)},
        ).json()["devices"]
        for device in devices:
            db.factory(
                "device",
                **{
                    "name": device["hostname"],
                    "ip_address": device["ip"] or device["hostname"],
                    "model": device["hardware"],
                    "operating_system": device["os"],
                    "os_version": device["version"],
                    "location": device["location"],
                    "latitude": device["lat"],
                    "longitude": device["lng"],
                },
            )


class TopologyImportForm(ServiceForm):
    form_type = HiddenField(default="topology_import_service")
    import_type = SelectField(
        choices=(
            ("librenms", "LibreNMS"),
            ("netbox", "Netbox"),
            ("opennms", "OpenNMS"),
        )
    )
    netbox_address = StringField(default="http://0.0.0.0:8000")
    netbox_token = PasswordField()
    opennms_address = StringField()
    opennms_devices = StringField()
    opennms_login = StringField()
    opennms_password = PasswordField()
    librenms_address = StringField(default="http://librenms.example.com")
    librenms_token = PasswordField()
    groups = {
        "Type of Import": {"commands": ["import_type"], "default": "expanded"},
        "Netbox": {
            "commands": ["netbox_address", "netbox_token"],
            "default": "expanded",
        },
        "OpenNMS": {
            "commands": [
                "opennms_address",
                "opennms_devices",
                "opennms_login",
                "opennms_password",
            ],
            "default": "expanded",
        },
        "LibreNMS": {
            "commands": ["librenms_address", "librenms_token"],
            "default": "expanded",
        },
    }

from sqlalchemy import ForeignKey, Integer

from xNMS.database import db
from xNMS.forms import LinkForm
from xNMS.fields import HiddenField, SelectField, StringField
from xNMS.models.inventory import Link


class EthernetLink(Link):
    __tablename__ = "ethernet_link"
    __mapper_args__ = {"polymorphic_identity": "ethernet_link"}
    pretty_name = "Ethernet Link"
    id = db.Column(Integer, ForeignKey("link.id"), primary_key=True)
    speed = db.Column(db.SmallString)
    standard = db.Column(db.SmallString)


class EthernetLinkForm(LinkForm):
    form_type = HiddenField(default="ethernet_link")
    speed = StringField("Serial Number", default=22)
    standard = SelectField(
        "Standard",
        choices=(
            ("10BASE2", "10BASE2"),
            ("10BASE5", "10BASE5"),
            ("10BASE-T", "10BASE-T"),
            ("1000BASE-T", "1000BASE-T"),
            ("10GBASE-T", "10GBASE-T"),
        ),
    )
    properties = ["speed", "standard"]

/*
global
xNMS: false
*/

// eslint-disable-next-line
function job(id) {
  const serviceType = "scrapli_netconf_service";
  const commandField = xNMS.automation.field("command", serviceType, id);
  const targetDiv = xNMS.automation.field("target-div", serviceType, id);
  commandField
    .on("change", function() {
      const command = commandField.val();
      if (command.includes("lock") || command.includes("config")) {
        targetDiv.show();
      } else {
        targetDiv.hide();
      }
    })
    .change();
  targetDiv.css("display", "none");
}

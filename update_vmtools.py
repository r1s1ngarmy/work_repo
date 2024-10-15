from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl

def access_and_update_templates(vcenter_host, username, password, template_names):
    # Connect to vSphere
    context = ssl._create_unverified_context()
    service_instance = SmartConnect(host=vcenter_host, user=username, pwd=password, sslContext=context)
    
    # Retrieve the content from the service instance
    content = service_instance.RetrieveContent()
    
    # Create a container view for Virtual Machines
    container = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    
    for template_name in template_names:
        # Search for the template
        template_found = False
        for managed_entity in container.view:
            if managed_entity.name == template_name and managed_entity.config.template:
                template_found = True
                print(f"Found template: {managed_entity.name}")
                
                # Convert to VM
                managed_entity.MarkAsVirtualMachine(pool=None, host=None)
                
                # Power on the VM
                task = managed_entity.PowerOn()
                while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
                    continue
                
                # Update VMware Tools
                managed_entity.UpgradeTools()  # Will handle reboot internally if needed
                
                # Power off and convert back to template
                managed_entity.PowerOff()
                managed_entity.MarkAsTemplate()
                print(f"Updated VMware Tools for template: {managed_entity.name}")
                break
        
        if not template_found:
            print(f"Template '{template_name}' not found.")
    
    Disconnect(service_instance)

# Example usage
template_names = ["template1_name", "template2_name", "template3_name"]
access_and_update_templates("your_vcenter_host", "your_username", "your_password", template_names)

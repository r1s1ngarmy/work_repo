from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl

def get_resource_pool(content, pool_name):
    # Retrieve the resource pool by name
    container = content.viewManager.CreateContainerView(content.rootFolder, [vim.ResourcePool], True)
    for resource_pool in container.view:
        if resource_pool.name == pool_name:
            return resource_pool
    return None

def wait_for_task(task):
    """Waits for a vSphere task to complete."""
    while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
        continue
    if task.info.state == vim.TaskInfo.State.error:
        raise Exception(f"Task failed: {task.info.error.msg}")
    return task.info.result

def upgrade_hardware_compatibility(vm):
    """Upgrades the hardware compatibility of a virtual machine."""
    print(f"Upgrading hardware compatibility for VM: {vm.name}")
    
    # Initiate hardware upgrade to the latest supported version
    task = vm.UpgradeVM_Task(version=None)  # `version=None` upgrades to the latest compatible version
    wait_for_task(task)
    print(f"Hardware upgrade completed for VM: {vm.name}")

def access_and_update_templates(vcenter_host, username, password, template_names, pool_name):
    # Connect to vSphere
    context = ssl._create_unverified_context()
    service_instance = SmartConnect(host=vcenter_host, user=username, pwd=password, sslContext=context)
    
    # Retrieve the content from the service instance
    content = service_instance.RetrieveContent()
    
    # Get the specified resource pool
    resource_pool = get_resource_pool(content, pool_name)
    if not resource_pool:
        print(f"Resource pool '{pool_name}' not found.")
        return
    
    # Create a container view for Virtual Machines
    container = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    
    for template_name in template_names:
        template_found = False
        for managed_entity in container.view:
            if managed_entity.name == template_name and managed_entity.config.template:
                template_found = True
                print(f"Found template: {managed_entity.name}")
                
                # Convert to VM
                managed_entity.MarkAsVirtualMachine(pool=resource_pool, host=None)
                
                # Power on the VM
                task = managed_entity.PowerOn()
                wait_for_task(task)  # Wait for the power-on task to complete
                
                # Upgrade Virtual Hardware Compatibility
                upgrade_hardware_compatibility(managed_entity)
                
                # Update VMware Tools
                managed_entity.UpgradeTools()  # Will handle reboot internally if needed
                
                # Power off the VM
                task = managed_entity.PowerOff()
                wait_for_task(task)  # Wait for the power-off task to complete
                
                # Convert back to template
                managed_entity.MarkAsTemplate()
                print(f"Updated VMware Tools and upgraded hardware compatibility for template: {managed_entity.name}")
                break
        
        if not template_found:
            print(f"Template '{template_name}' not found.")
    
    Disconnect(service_instance)

# Example usage
template_names = ["template1_name", "template2_name", "template3_name"]
access_and_update_templates("your_vcenter_host", "your_username", "your_password", template_names, "your_resource_pool_name")

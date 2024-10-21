import sys
import ssl
import winrm
import pyVmomi
import subprocess
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
from pyVim.task import WaitForTask
from resourcehandlers.vmware.pyvmomi_wrapper import wait_for_tasks
from common.methods import set_progress
from infrastructure.models import Server
from resourcehandlers.vmware.models import VsphereResourceHandler
from utilities.models import ConnectionInfo
from connectors.ansible.models import AnsibleConf

template_names = ["w10-1909-jxn-test", "w10-2004-jxn-test", "w10-21h2-jxn-test", "win11-22h2-jxn-test"]

def get_vmware_service_instance(vcenter_rh):
    try:
        context = ssl._create_unverified_context()
        si = SmartConnect(
            host=vcenter_rh.ip,
            user=vcenter_rh.serviceaccount,
            pwd=vcenter_rh.servicepasswd,
            sslContext=context
        )
        set_progress(f"Connected to vCenter at {vcenter_rh.ip}")
        return si
    except Exception as e:
        set_progress(f"Failed to connect to vCenter: {str(e)}")
        return None

def get_folder(content, folder_path):
    folder_levels = folder_path.split('/')
    container = content.rootFolder

    datacenters = [entity for entity in content.rootFolder.childEntity if isinstance(entity, vim.Datacenter)]
    for dc in datacenters:
        set_progress(f"Datacenter: {dc.name}, VM Folder: {dc.vmFolder.name}")
        container = dc.vmFolder

    for level in folder_levels:
        found = False
        for child in container.childEntity:
            if isinstance(child, vim.Folder) and child.name == level:
                container = child
                found = True
                break
        if not found:
            set_progress(f"Folder '{level}' not found.")
            return None

    set_progress(f"Folder '{folder_path}' found.")
    return container

def get_templates_from_folder(folder):
    templates = []
    for item in folder.childEntity:
        if isinstance(item, vim.VirtualMachine) and item.config.template:
            templates.append(item)
    set_progress(f"Found {len(templates)} template(s) in the folder.")
    return templates

def get_ansible_info(ansible_id):
    conn_info, _ = ConnectionInfo.objects.get_or_create(id=ansible_id)
    assert isinstance(conn_info, ConnectionInfo)
    username = conn_info.username
    password = conn_info.password
    address = conn_info.ip
    return username, password, address

def access_and_update_templates(vcenter_host, username, password, template_names):
    # Connect to vSphere
    context = ssl._create_unverified_context()
    service_instance = SmartConnect(host=vcenter_host, user=username, pwd=password, sslContext=context)

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
    try:
        set_progress(f"Upgrading hardware compatibility for VM: {vm.name}")
        
        # Initiate hardware upgrade to the latest supported version
        task = vm.UpgradeVM_Task(version=None)  # `version=None` upgrades to the latest compatible version
        wait_for_task(task)
        set_progress(f"Hardware upgrade completed for VM: {vm.name}")
    except vim.fault.AlreadyUpgraded as e:
        set_progress(f"Hardware is already up-to-date for VM: {vm.name}. Skipping upgrade.")
    except Exception as e:
        set_progress(f"Failed to upgrade hardware for VM: {vm.name}. Error: {str(e)}")

def run(job, logger=None, server=None, **kwargs):
    rh = VsphereResourceHandler.objects.get(name="Jackson vCenter")
    service_instance = get_vmware_service_instance(rh)
    
    # Retrieve the content from the service instance
    content = service_instance.RetrieveContent()

    # Get resource pool
    pool_name = "Support"
    resource_pool = get_resource_pool(content, pool_name)
    if not resource_pool:
        set_progress(f"Resource pool {pool_name} not found")
        return
    
    # Create a container view for Virtual Machines
    container = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    
    for template_name in template_names:
        # Search for the template
        template_found = False
        for managed_entity in container.view:
            if managed_entity.name == template_name and managed_entity.config.template:
                template_found = True
                set_progress(f"Found template: {managed_entity.name}")
                
                # Convert to VM
                managed_entity.MarkAsVirtualMachine(pool=resource_pool, host=None)
                set_progress(f"Converted {managed_entity.name} to VM")

                # Upgrade Virtual Hardware Compatibility (must be done while powered off)
                upgrade_hardware_compatibility(managed_entity)
                set_progress(f"Upgraded {managed_entity.name} to latest hardware version")
                
                # Power on the VM
                task = managed_entity.PowerOn()
                wait_for_task(task)  # Wait for the power-on task to complete
                set_progress(f"Powered {managed_entity.name} on")
                
                # Update VMware Tools
                managed_entity.UpgradeTools()  # Will handle reboot internally if needed
                set_progress(f"Upgraded {managed_entity.name} to latest VM tools version")
                
                # Power off the VM
                task = managed_entity.PowerOff()
                wait_for_task(task)  # Wait for the power-off task to complete
                set_progress(f"Powered {managed_entity.name} off")

                # Convert to template
                managed_entity.MarkAsTemplate()
                set_progress(f"Converted {managed_entity.name} to template")
                break
        
        if not template_found:
            set_progress(f"Template '{template_name}' not found.")
    
    Disconnect(service_instance)

    return "SUCCESS", "", "VMware Tools upgrade completed for all templates."

const FM_CHUNK_SIZE = 8 * 1024 * 1024; // 8 MB per slice
let currentUploadXhr = null;
let isUploadCancelled = false;

async function uploadFile(file, index) {
    if (isUploadCancelled) return;
    let parentPath = $("#location").val();
    const fileId = `file-${file.name.replace(/[^a-zA-Z0-9]/g, '-')}`;
    const progressBar = $(`#${fileId} .progress-bar`);
    const progressPercentage = $(`#${fileId} .progress-percentage`);
    const spinner = $(`#${fileId} .upload-spinner`);
    const removeBtn = $(`#${fileId} .remove-file`);

    spinner.show();
    removeBtn.hide();
    progressBar.removeClass('complete failed').css('width', '0%');
    progressPercentage.text('0%');

    const totalSize = file.size;
    const totalChunks = Math.max(1, Math.ceil(totalSize / FM_CHUNK_SIZE));
    const uploadId = 'fmup_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);

    for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
        if (isUploadCancelled) return;
        const start = chunkIndex * FM_CHUNK_SIZE;
        const end = Math.min(start + FM_CHUNK_SIZE, totalSize);
        const chunkBlob = file.slice(start, end);

        const formData = new FormData();
        formData.append('file', chunkBlob, file.name);
        formData.append('target_name', parentPath);
        formData.append('chunk_index', chunkIndex);
        formData.append('total_chunks', totalChunks);
        formData.append('total_file_size', totalSize);
        formData.append('file_name', file.name);
        formData.append('upload_id', uploadId);

        let success = false;
        let retryCount = 0;
        const maxRetries = 3;

        while (!success && retryCount < maxRetries && !isUploadCancelled) {
            try {
                const response = await new Promise((resolve, reject) => {
                    $.ajax({
                        url: upload_url,
                        type: 'POST',
                        data: formData,
                        processData: false,
                        contentType: false,
                        timeout: 0,
                        headers: { "X-CSRFToken": csrfToken },
                        xhr: function () {
                            const xhr = new window.XMLHttpRequest();
                            currentUploadXhr = xhr;
                            xhr.upload.addEventListener('progress', function (e) {
                                if (e.lengthComputable && !isUploadCancelled) {
                                    const overallLoaded = start + e.loaded;
                                    const percent = Math.min(99, Math.round((overallLoaded / totalSize) * 100));
                                    progressBar.css('width', `${percent}%`);
                                    progressPercentage.text(`${percent}%`);
                                }
                            }, false);
                            return xhr;
                        },
                        success: function (res) {
                            resolve(res);
                        },
                        error: function (xhr, status, err) {
                            reject(xhr);
                        }
                    });
                });

                if (isUploadCancelled) return;

                if (response.status === 'chunk_uploaded') {
                    success = true;
                    const chunkLoaded = end;
                    const percent = Math.min(99, Math.round((chunkLoaded / totalSize) * 100));
                    progressBar.css('width', `${percent}%`);
                    progressPercentage.text(`${percent}%`);
                } else if (response.status === 'success') {
                    spinner.hide();
                    progressBar.removeClass('failed').addClass('complete').css('width', '100%');
                    progressPercentage.html('<span style="color: #10b981; font-weight: 700;"><i class="fa fa-check-circle"></i> 100%</span>');
                    if (parentPath === "") {
                        parentPath = "/";
                    }
                    fetchFolderContents(parentPath);
                    return;
                } else {
                    throw new Error(response.message || 'Unknown response');
                }
            } catch (err) {
                if (isUploadCancelled) return;
                let errorMsg = 'Upload failed';
                if (err && err.responseJSON && err.responseJSON.message) {
                    errorMsg = err.responseJSON.message;
                } else if (err && err.responseText) {
                    try {
                        const parsed = JSON.parse(err.responseText);
                        if (parsed.message) errorMsg = parsed.message;
                    } catch(e) {
                        errorMsg = err.responseText.substring(0, 80);
                    }
                } else if (err && err.message) {
                    errorMsg = err.message;
                }

                // If non-recoverable error (e.g. quota, permissions, invalid), fail immediately
                if (err && (err.status === 403 || err.status === 400 || (errorMsg && errorMsg.toLowerCase().includes('quota')))) {
                    spinner.hide();
                    removeBtn.show();
                    progressBar.removeClass('complete').addClass('failed').css('width', '100%');
                    progressPercentage.html(`<span style="color: #ef4444; font-weight: 700;" title="${errorMsg}"><i class="fa fa-times-circle"></i> Failed</span>`);
                    notify.addNotification({
                        type: "error",
                        title: "Upload Failed",
                        message: errorMsg
                    });
                    return;
                }

                retryCount++;
                if (retryCount >= maxRetries) {
                    spinner.hide();
                    removeBtn.show();
                    progressBar.removeClass('complete').addClass('failed').css('width', '100%');
                    progressPercentage.html(`<span style="color: #ef4444; font-weight: 700;" title="${errorMsg}"><i class="fa fa-times-circle"></i> Failed</span>`);
                    notify.addNotification({
                        type: "error",
                        title: "Upload Failed",
                        message: errorMsg
                    });
                    console.log('Upload error:', err);
                    return;
                }
                await new Promise(r => setTimeout(r, 1000));
            }
        }
    }
}


$('#upload-button').on('click', async function () {
    const files = $('#file-input')[0].files;
    if (!files || files.length === 0) {
        alert('Please select files to upload.');
        return;
    }

    isUploadCancelled = false;
    const btn = $(this);
    btn.prop('disabled', true).html('<i class="fa fa-circle-o-notch fa-spin" style="margin-right: 6px;"></i> Uploading...');

    try {
        const uploadPromises = Array.from(files).map((file, index) => uploadFile(file, index));
        await Promise.all(uploadPromises);
    } finally {
        if (!isUploadCancelled) {
            btn.prop('disabled', false).html('Upload');
        }
    }
});

function fetchFolderList(path = "") {
    currentPath = path;  // Set current path for display and context actions
    $("#location").val(currentPath);

    $.ajax({
        url: folder_list_url,  // Endpoint for fetching folders
        method: "GET",
        data: { directory: path },
        dataType: "json",
        success: function(response) {
            $("#sub-folder").empty();  // Clear the sub-folder container

            if (response.status === "success") {
                response.entries.forEach(function(entry) {
                    if (entry.is_dir) {  // Only add folders to the list
                        // Create the folder item HTML structure with a "+" icon
                        const folderHTML = `
                            <div class="folder-item">
							<a href="javascript:void(0)" onclick="toggleSubfolder('${entry.path}', this)"><i class="fa fa-plus" ></i></a>
                                   
                                       
                                        <a href="javascript:void(0)" onclick="fetchFolderContents('${entry.path}')"> <i class="fa fa-folder" style="color:#F19E39"></i> ${entry.name}</a>
                                  <div class="subfolder-list" id="subfolder-${entry.name}" style="display: none;"></div>
                            </div>
                        `;

                        // Append the folder item to #sub-folder
                        $("#sub-folder").append(folderHTML);
						toggleSubfolder(entry.path, $(".folder-item:last-child a")[0]);
                    }
                });
            }
        },
        error: function(error) {
            console.error("Error fetching folder contents:", error);
        }
    });
}

	
function toggleSubfolder(path, button) {
    const subfolderContainer = $(button).siblings(".subfolder-list");

    // Check if the subfolder content is already loaded
    if (subfolderContainer.is(":visible")) {
        // Hide the subfolder if it's already displayed
        subfolderContainer.hide();
        $(button).find("i").removeClass("fa-minus").addClass("fa-plus");  // Change icon back to "+"
    } else {
        // Show and fetch subfolder contents if not already displayed
        $.ajax({
            url: folder_list_url,
            method: "GET",
            data: { directory: path },
            dataType: "json",
            success: function(response) {
                if (response.status === "success") {
                    // Empty the container before adding new content
                    subfolderContainer.empty();

                    response.entries.forEach(function(entry) {
                        if (entry.is_dir) {
                            // Add each subfolder with a "+" button to expand further if needed
                            const subfolderHTML = `
                                <div class="folder-item">
								<a href="javascript:void(0)" onclick="toggleSubfolder('${entry.path}', this)"> <i class="fa fa-plus" ></i></a>
                                   
                                        
                                         <a href="javascript:void(0)" onclick="fetchFolderContents('${entry.path}')"><i class="fa fa-folder" style="color:#F19E39"></i> ${entry.name}</a>
                                       
                                    
                                    <div class="subfolder-list" id="subfolder-${entry.name}" style="display: none;"></div>
                                </div>
                            `;
                            subfolderContainer.append(subfolderHTML);
							
							
                        }
                    });

                    // Show the subfolder container and update the icon
                    subfolderContainer.show();
                   // $(button).find("i").text("remove");  // Change icon to "-"
					$(button).find("i").removeClass("fa-plus").addClass("fa-minus");
					
					
                }
            },
            error: function(error) {
                console.error("Error fetching subfolder contents:", error);
            }
        });
    }
}	
	
function fetchFolderContentsx(path = "") {
            currentPath = path;  // Set current path for display and context actions
            $("#location").val(currentPath);
  $("#loading-container").show();
            $.ajax({
                url: file_folder_list_url,  // Endpoint for fetching files and folders
                method: "GET",
                data: { directory: path },
                dataType: "json",
                success: function(response) {
                   $("#file-list").empty(); 
                    if (response.status === "success") {
                        response.entries.forEach(function(entry) {
                    // Determine if the item is a folder or file and set the icon accordingly
                    const icon = entry.icon;
					
                    const itemType = entry.is_dir ? "folder" : "file";

                    // Format the last modified time if it's provided
                    const lastModified = entry.modified_time ? new Date(entry.modified_time).toLocaleString() : "Unknown";
                    
                    // Create the item HTML structure with lazy loading
                    const itemHTML = `
                        <div class="item" id="${itemType}" data-path="${entry.path}" role="button" tabindex="0" draggable="true" 
                             data-dir="${entry.is_dir}" data-type="${itemType}" data-name="${entry.name}" 
                             aria-label="${entry.name}" aria-selected="false" data-ext=".${entry.extension}" data-permission="${entry.permissions}">
                            <div><img src="${icon}" alt="${entry.name} Icon" /></div>
                            <div>
                                <p class="name">${entry.name}</p>
                                <p class="size" data-order="${entry.size}">${entry.size}</p>
                                <p class="modified"><time datetime="${entry.modified}">${lastModified}</time></p>
                                <p class="permission">${entry.permissions}</p>
                            </div>
                        </div>
                    `;
                    
                    // Append the item to #file-list
                    $("#file-list").append(itemHTML);
                });
                   
 attachClickEventListeners();
				   }
					$("#loading-container").hide();
                },
                error: function(error) {
				$("#loading-container").hide();
                   // console.error("Error fetching folder contents:", error);
                }
            });
        }
		
function actionPopupF() {
let parentPath = $("#location").val();
let target="";
let permissions="";
$("#loading-containera").show();
 const title = $("#atitle").text();  // Get the title text
    const path = $("#apath").val();  // Get the label text
	const folderPath = path.substring(0, path.lastIndexOf("/"));
    const targetName = $("#anames").val();  // Get the input value
    let actionType = $("#aaction").text(); 
	if (!$("#delete").prop("checked") && actionType=="Delete") {
actionType="Trash";
}
	
	
 
	
	
	
	
if(actionType=="Copy" || actionType=="Move" || actionType=="Unzip" || actionType=="Compress"){
target=targetName;
}else if (!$("#delete").prop("checked") && $("#aaction").text()=="Delete") {
target='.trash/'+targetName;
}else if(actionType=="New File" || actionType=="New Folder"){
target=parentPath+'/'+targetName;
}
else{
target=folderPath+'/'+targetName;
}

if(actionType=="New File" || actionType=="New Folder"){
actionType = actionType.replace(/ /g, "_");
}
if(actionType=="Permission"){
 permissions = $("#u").val() + $("#g").val() + $("#w").val();

}
const selectedItems = getSelectedItems(); 
    // Log the data object to debug
    const requestData = {
        action: actionType,  // Convert action to lowercase
        file_name: path,
		permission: permissions,
        target_name: target,
		selected_items: selectedItems,
		base: parentPath+'/'
    };

  //  console.log("Request Data:", requestData);
	
	
	$.ajax({
         url: actionUrl,
        method: "POST",
        data: requestData,
        headers: { "X-CSRFToken": csrfToken },
        dataType: "json",
        success: function(response) {
		
            if (response.status === "success") {
                notify.addNotification({
                    type: "success",
                    title: "Success!",
                    message: `${response.message}`
                });
                aclosePopup();

                // Fetch parent folder contents
                if (parentPath === "") {
                    parentPath = "/";
                }
                fetchFolderContents(parentPath);
            } else {
                notify.addNotification({
                    type: "error",
                    title: "Error!",
                    message: `Failed: ${response.message}`
                });
            }
            $("#loading-containera").hide();
        },
        error: function(jqXHR, textStatus, errorThrown) {
            $("#loading-containera").hide();
 aclosePopup();
            // Extract and display the error message
            let errorMessage = "An unknown error occurred.";
            if (jqXHR.responseJSON && jqXHR.responseJSON.message) {
                errorMessage = jqXHR.responseJSON.message;
            } else if (jqXHR.responseText) {
                errorMessage = jqXHR.responseText;
            } else if (errorThrown) {
                errorMessage = errorThrown;
            }

            notify.addNotification({
                type: "error",
                title: "Error!",
                message: `Failed: ${errorMessage}`
            });

            console.error("Error details:", {
                jqXHR,
                textStatus,
                errorThrown
            });
	 }
	  });
	
}		
function downloadFileDirectly(selectedItemname, selectedItem) {
    const selectedItems = getSelectedItems(); // Ensure this function returns the right selected items
    const path = $("#location").val() + '/' + selectedItemname;  // Construct the path for the file
    const formData = new FormData();
    formData.append('action', 'download');
    formData.append('file_name', path);  // Send the file path to the backend
    formData.append('target_name', $("#location").val());  // Send the target location
    formData.append('selected_items', JSON.stringify(selectedItems));  // Send selected items as a JSON string

    // Make the fetch request
    fetch(actionUrl, {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken },
        body: formData,
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errorData => {
                throw new Error(errorData.message || "Download failed");
            });
        }
        return response.blob();  // Get the response as a blob (file content)
    })
    .then(blob => {
        // Create a blob URL and trigger download
        const link = document.createElement('a');
        link.href = window.URL.createObjectURL(blob);
        link.download = selectedItemname;  // Use the selected item's name for the download
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);  // Clean up by removing the link after clicking
    })
    .catch(error => {
        console.error("Download error:", error);
        // Optionally show an alert or a notification
        // alert("Error: " + error.message);
    });
}
		
document.addEventListener('click', function(event) {
    var nav = document.querySelector('nav');
    var menuButton = document.querySelector('.menu-button');

    if (!nav || !menuButton) return;

    // Only auto-close on outside click if on mobile (screen width <= 768)
    if (window.innerWidth <= 768) {
        if (!nav.contains(event.target) && !menuButton.contains(event.target)) {
            if (nav.classList.contains('active')) {
                nav.classList.remove('active');
            }
        }
    }
});

function toggleSidebar() {
    var nav = document.querySelector('nav');
    var body = document.body;

    if (window.innerWidth <= 768) {
        if (nav) {
            nav.classList.toggle('active');
        }
    } else {
        body.classList.toggle('sidebar-collapsed');
        if (nav && nav.classList.contains('active')) {
            nav.classList.remove('active');
        }
        try {
            localStorage.setItem('fm_sidebar_collapsed', body.classList.contains('sidebar-collapsed') ? 'true' : 'false');
        } catch (e) {}
    }
}

// Restore sidebar state from localStorage on load
if (window.innerWidth > 768) {
    try {
        if (localStorage.getItem('fm_sidebar_collapsed') === 'true') {
            document.body.classList.add('sidebar-collapsed');
        }
    } catch (e) {}
}

function getSelectedItems() {
    const allItems = document.querySelectorAll('.item');
    const selectedItems = document.querySelectorAll('.item[aria-selected="true"]');
    
    if (selectedItems.length > 1) {
        // Return only selected items data-paths if multiple selected
        return Array.from(selectedItems).map(item => item.dataset.path);
    } else {
		 return [];
		
	}
}

function showSelectedItems() {
    const selectedItems = getSelectedItems();
    const listContainer = document.getElementById('selected-items-list');
    const cfName = document.getElementById('cf-name');
    listContainer.style.display = 'none';
    listContainer.innerHTML = '';
    cfName.style.display = 'block';

    // Hide all if nothing selected
    if (selectedItems.length === 0) {
        cfName.style.display = 'block';
        listContainer.style.display = 'none';
        return;
    }

    // Show list container and hide single item span
    listContainer.style.display = 'block';
    cfName.style.display = 'none';

    // Clear and rebuild list
    listContainer.innerHTML = '';

    const header = document.createElement('div');
    header.style.cssText = 'display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px solid #e2e8f0; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b;';
    header.innerHTML = `<span>Selected Items (${selectedItems.length})</span><span style="font-size: 11px; color: #94a3b8; font-weight: normal;">scroll to view</span>`;
    listContainer.appendChild(header);

    const ul = document.createElement('ul');
    ul.style.listStyle = 'none';
    ul.style.padding = '0';
    ul.style.margin = '0';

    selectedItems.forEach(path => {
        const li = document.createElement('li');
        const cleanPath = path.replace(/^-/, '');
        
        const icon = document.createElement('i');
        icon.className = 'fa fa-file-o';
        icon.style.cssText = 'color: #94a3b8; font-size: 11px; margin-right: 6px; flex-shrink: 0;';
        
        const textSpan = document.createElement('span');
        textSpan.style.cssText = 'word-break: break-all; flex: 1;';
        textSpan.textContent = cleanPath;
        textSpan.title = cleanPath;
        
        li.appendChild(icon);
        li.appendChild(textSpan);
        ul.appendChild(li);
    });

    listContainer.appendChild(ul);
}



function checkIfAnyItemSelected() {
    const selectedItems = document.querySelectorAll('#file-list .item[aria-selected="true"]');
    const unselectBtn = document.getElementById('unselect-all-btn');
    
    // If at least one item is selected, remove the 'disabled' class from the 'Unselect All' button
    if (selectedItems.length > 0) {
        unselectBtn.closest('li').classList.remove('disabled');
    } else {
        // If no item is selected, add the 'disabled' class to the 'Unselect All' button
        unselectBtn.closest('li').classList.add('disabled');
    }
}

// Function to select all items
function selectAll() {
    const items = document.querySelectorAll('#file-list .item');
    items.forEach(item => {
        item.setAttribute('aria-selected', 'true');
    });
    
    checkIfAnyItemSelected();
}

// Function to unselect all items
function unselectAll() {
    const items = document.querySelectorAll('#file-list .item');
    items.forEach(item => {
        item.setAttribute('aria-selected', 'false');
    });
    
    checkIfAnyItemSelected();
}

function toggleItemSelection(event) {
    const item = event.currentTarget;

    if (event.ctrlKey || event.metaKey) {
        // If Ctrl/Cmd is held, toggle selection (multi-select behavior)
        const isSelected = item.getAttribute('aria-selected') === 'true';
        item.setAttribute('aria-selected', isSelected ? 'false' : 'true');
    } else {
        // If Ctrl/Cmd is NOT held, deselect all other items and select only this one
        const allItems = document.querySelectorAll('#file-list .item');
        allItems.forEach(i => {
            i.setAttribute('aria-selected', i === item ? 'true' : 'false');
        });
    }

    if (item.getAttribute('aria-selected') === 'true') {
        selectedItemPath = $(item).data("path"); 
        selectedtype = $(item).data("type");
        selectedfname = $(item).data("name");
        selectedfext = $(item).data("ext");
        selectedpermission = $(item).data("permission");
        $("#select_path").val(selectedItemPath);
        $("#select_file_name").val(selectedfname);
        $("#select_type").val(selectedtype);
        $("#select_ext").val(selectedfext);
        $("#select_permission").val(selectedpermission);
    }

    checkIfAnyItemSelected();
}


// Attach event listeners to the buttons
document.getElementById('select-all-btn').addEventListener('click', selectAll);
document.getElementById('unselect-all-btn').addEventListener('click', unselectAll);



function attachClickEventListeners() {
   // Attach event listener to items for selection toggling
const items = document.querySelectorAll('#file-list .item');
items.forEach(item => {
    item.addEventListener('click', toggleItemSelection);
});
}
const popupSettings = document.getElementById('action-popup_settings');
const actionpopup = document.getElementById('action-popup');
const del = document.getElementById('del');
const per = document.getElementById('per');
const all = document.getElementById('all');
const aclose = document.getElementById('aclose');
const atitle = document.getElementById('atitle');

const anames = document.getElementById('anames');
const apath = document.getElementById('apath');
const ahome = document.getElementById('ahome');
    
// Select elements

const newFolderButton = document.getElementById('new-folder');
const newFileButton = document.getElementById('new-file');
const cancelButton = document.getElementById('cancel-button');

const nameInput = document.getElementById('name');
const ttile = document.getElementById('ttile');
const aaction = document.getElementById('aaction');
const cfname = document.getElementById('cf-name');



function openactionPopup(type, selectedItemname, selectedItem) {
    const listContainer = document.getElementById('selected-items-list');
    const cfName = document.getElementById('cf-name');
    // Reset display states and clear content
    listContainer.style.display = 'none';
    listContainer.innerHTML = '';
    cfName.style.display = 'block';
    anames.style.display = 'block';
    if (type !== "Rename") {
        showSelectedItems();
    }
    if (type === "Delete") {
        del.style.setProperty('display', 'flex', 'important');
        all.style.setProperty('display', 'none', 'important');
        per.style.setProperty('display', 'none', 'important');
    } else if (type === "Permission") {
        per.style.setProperty('display', 'flex', 'important');
        all.style.setProperty('display', 'none', 'important');
        del.style.setProperty('display', 'none', 'important');
    } else if (type === "Fix-Permission") {
        all.style.setProperty('display', 'flex', 'important');
        del.style.setProperty('display', 'none', 'important');
        per.style.setProperty('display', 'none', 'important');
        anames.style.setProperty('display', 'none', 'important');
    } else {
        all.style.setProperty('display', 'flex', 'important');
        del.style.setProperty('display', 'none', 'important');
        per.style.setProperty('display', 'none', 'important');
    }
    cfname.innerHTML = type + ": " + selectedItemname;
    actionpopup.style.display = 'flex';

    if (type === "Copy" || type === "Move" || type === "Unzip") {
        ahome.style.display = 'block';
        anames.value = $("#location").val();
        anames.placeholder = "Destination path (relative to home)";
    } else if (type === "Compress") {
        ahome.style.display = 'block';
        anames.value = $("#location").val() + '/' + selectedItemname + '.zip';
        anames.placeholder = "Archive path";
    } else if (type === "Rename") {
        ahome.style.display = 'none';
        anames.value = selectedItemname;
        anames.placeholder = "New name";
    } else if (type === "New File") {
        ahome.style.display = 'none';
        anames.value = '';
        anames.placeholder = "Enter file name";
    } else if (type === "New Folder") {
        ahome.style.display = 'none';
        anames.value = '';
        anames.placeholder = "Enter folder name";
    } else {
        ahome.style.display = 'none';
        anames.value = selectedItemname;
    }

    apath.value = selectedItem;
    atitle.innerHTML = type; // Update the title
    aaction.innerHTML = type; // Update the action
}

function aclosePopup() {
    del.style.setProperty('display', 'none', 'important');
    all.style.setProperty('display', 'none', 'important');
    per.style.setProperty('display', 'none', 'important');
    actionpopup.style.display = 'none';
    ahome.style.display = 'none';
    anames.value = ''; // Clear input field
    atitle.innerHTML = '';
    aaction.innerHTML = '';
    apath.value = '';
    cfname.innerHTML = '';
    $("#loading-containera").hide();
}




aclose.addEventListener('click', aclosePopup);
aaction.addEventListener('click', actionPopupF);


// Function to open the popup with placeholder text
function openPopup(placeholderText) {
    popup.style.display = 'flex';
    nameInput.placeholder = placeholderText+" name";
    nameInput.value = ''; // Clear input field
    ttile.innerHTML = 'New '+placeholderText; // Clear input field
}


// Function to close the popup
function closePopup() {
    popup.style.display = 'none';
    nameInput.value = ''; // Clear input field
    ttile.innerHTML = '';
}

function openPopupSettings() {
    popupSettings.style.display = 'flex';
   
}


// Function to close the popup
function closePopupSettings() {
    popupSettings.style.display = 'none';
   
}



function saveSettings() {
    let parentPath = $("#location").val();
    const requestData = {
        hide_hiden_file: $("#hidden").is(":checked") ? 1 : 0,
        hide_folder_size: $("#folder_size").is(":checked") ? 1 : 0,
        // Add other settings if needed
    };

    // Show loading indicator
    $("#loading-containera").show();

    $.ajax({
        url: saveUrl,
        method: "POST",
        data: requestData,
        headers: { "X-CSRFToken": csrfToken },
        dataType: "json",
        success: function(response) {
			closePopupSettings();
            if (response.status === "success") {
                notify.addNotification({
                    type: "success",
                    title: "Success!",
                    message: `${response.message}`
                });
                aclosePopup();

                if (parentPath === "") {
                    parentPath = "/";
                }
                fetchFolderContents(parentPath);
            } else {
                notify.addNotification({
                    type: "error",
                    title: "Error!",
                    message: `Failed: ${response.message}`
                });
            }
            $("#loading-containera").hide();
        },
        error: function(jqXHR, textStatus, errorThrown) {
			closePopupSettings();
            $("#loading-containera").hide();
            aclosePopup();

            let errorMessage = "An unknown error occurred.";
            if (jqXHR.responseJSON && jqXHR.responseJSON.message) {
                errorMessage = jqXHR.responseJSON.message;
            } else if (jqXHR.responseText) {
                errorMessage = jqXHR.responseText;
            } else if (errorThrown) {
                errorMessage = errorThrown;
            }

            notify.addNotification({
                type: "error",
                title: "Error!",
                message: `Failed: ${errorMessage}`
            });

            
        }
    });
}





let selectedFiles = [];
const uploadModal = document.getElementById('upload-modal');
const openUploadModalButton = document.getElementById('open-upload-modal');
const cancelUploadButton = document.getElementById('cancel-upload-button');
const uploadButton = document.getElementById('upload-button');
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const filePreview = document.getElementById('file-preview');
const fileSelectButton = document.getElementById('file-select-button');

// Open and close modal functions
function openUploadModal() {
    isUploadCancelled = false;
    uploadModal.style.display = 'flex';
    filePreview.innerHTML = ''; // Clear previous file preview
}

function closeUploadModal() {
    isUploadCancelled = true;
    if (currentUploadXhr) {
        try {
            currentUploadXhr.abort();
        } catch (e) {
            console.error('Error aborting upload:', e);
        }
        currentUploadXhr = null;
    }
    uploadModal.style.display = 'none';
    fileInput.value = ''; // Clear selected files
    filePreview.innerHTML = ''; // Clear file preview
    $('#upload-button').prop('disabled', false).html('Upload');
    $('#upload-button-url').prop('disabled', false).html('Upload');
    $('#prog').hide();
    $('#url-input').val('');
}

// Trigger open modal ONLY on button click
openUploadModalButton.addEventListener('click', openUploadModal);

// Close modal on cancel button clicks (top-right X, bottom Cancel buttons)
cancelUploadButton.addEventListener('click', closeUploadModal);
$('#cancel-upload-btn').on('click', closeUploadModal);
$('#cancel-upload-url-btn').on('click', closeUploadModal);

// Trigger file input when select button is clicked
fileSelectButton.addEventListener('click', () => fileInput.click());

// Handle file selection from file input
fileInput.addEventListener('change', handleFiles);

function handleFiles(event) {
    isUploadCancelled = false;
    const files = event.target.files || event.dataTransfer.files;
    if (!files || files.length === 0) return;

    // Update the file input with the selected or dropped files
    fileInput.files = files;

    const filePreview = document.getElementById('file-preview');
    filePreview.innerHTML = Array.from(files)
        .map(file => {
            const fileId = `file-${file.name.replace(/[^a-zA-Z0-9]/g, '-')}`;
            return `
                <div class="file-item" id="${fileId}">
                    <div class="file-item-header">
                        <div class="file-item-info">
                            <i class="fa fa-file-text-o"></i>
                            <span class="file-item-name" title="${file.name}">${file.name}</span>
                            <span class="file-item-size">(${formatFileSize(file.size)})</span>
                        </div>
                        <div class="file-item-status">
                            <i class="fa fa-circle-o-notch fa-spin upload-spinner" style="display: none;"></i>
                            <span class="progress-percentage">0%</span>
                            <button type="button" class="remove-file" title="Remove" onclick="removeFile(this, '${fileId}')">&times;</button>
                        </div>
                    </div>
                    <div class="progress-container">
                        <div class="progress-bar" style="width: 0%;"></div>
                    </div>
                </div>
            `;
        })
        .join('');
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    else if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    else if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
    else return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
}

// Function to handle the removal of a file preview
function removeFile(button, fileId) {
    if (fileId) {
        $(`#${fileId}`).remove();
    } else {
        $(button).closest('.file-item').remove();
    }
    if ($('#file-preview .file-item').length === 0) {
        fileInput.value = '';
    }
}


// Handle drag-and-drop functionality
dropZone.addEventListener('dragover', (event) => {
    event.preventDefault();
    dropZone.classList.add('dragging');
});

dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragging'));

dropZone.addEventListener('drop', (event) => {
    event.preventDefault();
    dropZone.classList.remove('dragging');
    handleFiles(event); // Process dropped files
	 fileInput.files = event.dataTransfer.files;
});

/*
uploadButton.addEventListener('click', () => {
    const files = fileInput.files;
    if (files.length === 0) {
        alert('Please select a file to upload.');
        return;
    }

    // Upload logic here
   // console.log('Uploading files:', files);
    closeUploadModal(); // Close modal after upload
});
*/
// Close modal if clicking outside the content
uploadModal.addEventListener('click', (e) => {
    if (e.target === uploadModal) closeUploadModal();
});

 
document.addEventListener("DOMContentLoaded", function() {
    const lazyImages = document.querySelectorAll("img.lazy-load");

    const loadImage = (image) => {
        image.src = image.getAttribute("data-src");
        image.classList.remove("lazy-load");
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                loadImage(entry.target);
                observer.unobserve(entry.target);
            }
        });
    }, { rootMargin: "0px 0px 100px 0px" });

    lazyImages.forEach(image => observer.observe(image));
});
 

function calcperm() {
    // Get values for user, group, and world
    var userPerm = 0;
    var groupPerm = 0;
    var worldPerm = 0;

    // User permissions
    if (document.querySelector('input[name="ur"]:checked')) userPerm += 4; // Read
    if (document.querySelector('input[name="uw"]:checked')) userPerm += 2; // Write
    if (document.querySelector('input[name="ux"]:checked')) userPerm += 1; // Execute

    // Group permissions
    if (document.querySelector('input[name="gr"]:checked')) groupPerm += 4; // Read
    if (document.querySelector('input[name="gw"]:checked')) groupPerm += 2; // Write
    if (document.querySelector('input[name="gx"]:checked')) groupPerm += 1; // Execute

    // World permissions
    if (document.querySelector('input[name="wr"]:checked')) worldPerm += 4; // Read
    if (document.querySelector('input[name="ww"]:checked')) worldPerm += 2; // Write
    if (document.querySelector('input[name="wx"]:checked')) worldPerm += 1; // Execute
document.querySelector('input[name="vu"]').value = userPerm;
    document.querySelector('input[name="vg"]').value = groupPerm;
    document.querySelector('input[name="vw"]').value = worldPerm;
    // Set the permission values
    document.querySelector('input[id="u"]').value = userPerm;
    document.querySelector('input[id="g"]').value = groupPerm;
    document.querySelector('input[id="w"]').value = worldPerm;
}

 // Corrected function with proper jQuery selector
function setPermission(permission) {
    // Ensure the permission value is a string and has a length of 3
    permission = permission.toString();
    if (permission.length !== 3) {
        console.error("Invalid permission value");
        return;
    }

    // Split permission into user, group, and world components
    const user = parseInt(permission[0]);
    const group = parseInt(permission[1]);
    const world = parseInt(permission[2]);

    // Helper function to set checkboxes based on permission
    function setCheckboxes(scope, value) {
        // Clear all checkboxes for this scope
        $(`input[name^="${scope}"]`).prop('checked', false);

        // Set checkboxes based on value
        if (value & 4) $(`input[name="${scope}r"]`).prop('checked', true); // Read
        if (value & 2) $(`input[name="${scope}w"]`).prop('checked', true); // Write
        if (value & 1) $(`input[name="${scope}x"]`).prop('checked', true); // Execute
    }

    // Set checkboxes for user, group, and world
    setCheckboxes("u", user); // User permissions
    setCheckboxes("g", group); // Group permissions
    setCheckboxes("w", world); // World permissions

    // Update readonly text fields (ensure these input IDs are correct)
    $('input[name="vu"]').val(user);
    $('input[name="vg"]').val(group);
    $('input[name="vw"]').val(world);

    // Update text fields with correct permission values
    $('input[id="u"]').val(user);
    $('input[id="g"]').val(group);
    $('input[id="w"]').val(world);
}

 
    $(document).ready(function() {
	

	
	
        let selectedItem = null;
		let selectedItemname = null;
        let currentPath = "";
		let itemper="";

        // Function to fetch and display folder list in the left panel
       // Function to fetch and display contents of the selected folder in the right panel

// Function to toggle subfolder display




        // Function to fetch and display contents of the selected folder in the right panel
        

        // Initial load of the folder list and root folder contents
       fetchFolderList();
        fetchFolderContents();
/*
        // Handle folder click to load contents on the right panel
        $(document).on("dblclick", "[id^=folder]", function() {
            const folderPath = $(this).data("path");
            fetchFolderContents(folderPath);
        });
		*/
let lastTap = 0;

$(document).on("click", "[id^=folder]", function() {
    const currentTime = new Date().getTime();
    const timeDiff = currentTime - lastTap;

    if (timeDiff < 300 && timeDiff > 0) {
        const folderPath = $(this).data("path");
        fetchFolderContents(folderPath);
    }

    lastTap = currentTime;
});



        // Right-click handler for folder and file items
        $(document).on("contextmenu", "[id^=folder], [id^=file]", function(e) {
            e.preventDefault();
			e.stopPropagation();
			
			const item = e.currentTarget;
			const isSelected = item.getAttribute('aria-selected') === 'true';

        if (!isSelected) {
            // Deselect all, then select only this item
            const allItems = document.querySelectorAll('#file-list .item');
            allItems.forEach(i => {
                i.setAttribute('aria-selected', i === item ? 'true' : 'false');
            });
        }
		
		 checkIfAnyItemSelected();
		
		
            selectedItem = $(this).data("path");
			selectedItemname = $(this).data("name");
			 itemper = $(this).data("permission");
			const itemType = $(this).data("type");
			const itemext = $(this).data("ext");
			
			//console.log("Selected item path:", selectedItem);
            $("#context-menu").css({
                top: e.pageY + "px",
                left: e.pageX + "px"
            }).show();
			
			if (itemType === "folder") {
        $("#menu-download").css("display", "none");
		$("#menu-view").css("display", "none");
		$("#menu-edit").css("display", "none");
		$("#menu-html-edit").css("display", "none");
    } else {
         $("#menu-download").css("display", "block");
		$("#menu-view").css("display", "block");
		$("#menu-edit").css("display", "block");
		$("#menu-html-edit").css("display", "block");
    }
			
	if (itemext === ".zip" || itemext === ".gz") {
$("#menu-view").css("display", "none");
		$("#menu-edit").css("display", "none");
		$("#menu-html-edit").css("display", "none");	
		$("#menu-extract").css("display", "block");	
		}else{
		$("#menu-extract").css("display", "none");	
		}	
        });
		
		

		
		
	
        // Hide the context menu when clicking outside
        $(document).click(function(e) {
            if (!$(e.target).closest("#context-menu").length) {
                $("#context-menu").hide();
            }
        });

$("#menu-edit").click(function() {
    $("#context-menu").hide();
    if (selectedItem) {
        // Open the editor page in a new tab with the selected file path as a query parameter
        window.open(php_editor+`?file=${encodeURIComponent(selectedItem)}`, '_blank');
    } else {
        alert("No file selected for editing.");
    }
});

$("#menu-view").click(function() {
    $("#context-menu").hide();
    if (selectedItem) {
        // Open the editor page in a new tab with the selected file path as a query parameter
        window.open( view+ `?file=${encodeURIComponent(selectedItem)}&view=1`, '_blank');
    } else {
        alert("No file selected for editing.");
    }
});
$("#menu-html-edit").click(function() {
    $("#context-menu").hide();
    if (selectedItem) {
        // Open the editor page in a new tab with the selected file path as a query parameter
        window.open(php_editor + `?file=${encodeURIComponent(selectedItem)}&ext=html`, '_blank');
    } else {
        alert("No file selected for editing.");
    }
});
      

        $("#menu-delete").click(function() {
            if (selectedItem) {
        openactionPopup("Delete",selectedItemname,selectedItem);
    } else {
        alert("No file or folder selected");
    }
            $("#context-menu").hide();
        });

        $("#menu-copy").click(function() {
           if (selectedItem) {
        openactionPopup("Copy",selectedItemname,selectedItem);
    } else {
        alert("No file selected");
    }
            $("#context-menu").hide();
            // Add code for copying the file or folder
        });
		
		 $("#menu-rename").click(function() {
		 if (selectedItem) {
        openactionPopup("Rename",selectedItemname,selectedItem);
    } else {
        alert("No file selected");
    }
          
            $("#context-menu").hide();
            // Add code for copying the file or folder
        });

        $("#menu-move").click(function() {
            if (selectedItem) {
        openactionPopup("Move",selectedItemname,selectedItem);
    } else {
        alert("No file selected");
    }
            $("#context-menu").hide();
            // Add code for moving the file or folder
        });

$("#menu-extract").click(function() {
            if (selectedItem) {
        openactionPopup("Unzip",selectedItemname,selectedItem);
    } else {
        alert("No file selected");
    }
            $("#context-menu").hide();
            // Add code for moving the file or folder
        });

$("#menu-compress").click(function() {
            if (selectedItem) {
        openactionPopup("Compress",selectedItemname,selectedItem);
    } else {
        alert("No file selected");
    }
            $("#context-menu").hide();
            // Add code for moving the file or folder
        });


$("#menu-download").click(function() {
            if (selectedItem) {
        //openactionPopup("Download",selectedItemname,selectedItem);
		window.open(download_url+`?file=${encodeURIComponent(selectedItem)}`, '_blank');
    } else {
        alert("No file selected");
    }
            $("#context-menu").hide();
            // Add code for moving the file or folder
        });

        $("#menu-permissions").click(function() {
		
		 $("#context-menu").hide();
		 if (selectedItem) {
         openactionPopup("Permission",selectedItemname,selectedItem);
		 setPermission(itemper);
    } else {
        alert("No file or folder selected");
    }
           
           
            // Add code for changing permissions
        });

        // Function to delete a file or folder
       

        // Prevent default context menu from appearing
        $(document).on("contextmenu", function(e) {
            //e.preventDefault();
        });
		
	$("#file-list").on("click", ".item", function() {
    selectedItemPath = $(this).data("path"); 
	selectedtype = $(this).data("type");
	selectedfname = $(this).data("name");
	selectedfext = $(this).data("ext");
	selectedpermission = $(this).data("permission");
	$("#select_path").val(selectedItemPath);
	$("#select_file_name").val(selectedfname);
	 $("#select_type").val(selectedtype);
	  $("#select_ext").val(selectedfext);
	  $("#select_permission").val(selectedpermission);
    
});	
		
// When the Back button is clicked
$("#back-button").click(function() {
    // Get the current directory (you should already have this variable set)
    let currentPath = $("#location").val();

    // Calculate the parent directory by removing the last part of the current path
    let parentPath = currentPath.substring(0, currentPath.lastIndexOf('/'));

    // If there is no parent path (i.e., we are at the root), don't navigate further
    if (parentPath === "") {
        parentPath = "/";
    }

    // Fetch the contents of the parent directory
    fetchFolderContents(parentPath);
});
// When the Back button is clicked
$("#home-button").click(function() {
        parentPath = "/";
    fetchFolderContents(parentPath);
}); 


$("#view-trash").click(function() {
        parentPath = ".trash";
    fetchFolderContents(parentPath);
}); 		

  	
$("#top-edit").click(function() {
   let selectedItem = $("#select_path").val();
   let selectedtype = $("#select_type").val();
    if (selectedItem && selectedtype=='file') {
        // Open the editor page in a new tab with the selected file path as a query parameter
        window.open(php_editor + `?file=${encodeURIComponent(selectedItem)}`, '_blank');
    } else {
        alert("No file selected for editing.");
    }
});

$("#top-edit-html").click(function() {
   let selectedItem = $("#select_path").val();
   let selectedtype = $("#select_type").val();
    if (selectedItem && selectedtype=='file') {
        // Open the editor page in a new tab with the selected file path as a query parameter
        window.open(php_editor + `?file=${encodeURIComponent(selectedItem)}&ext=html`, '_blank');
    } else {
        alert("No file selected for editing.");
    }
});
// When the Back button is clicked
$("#btnGo,#refresh").click(function() {
    // Get the current directory (you should already have this variable set)
    let parentPath = $("#location").val();

    
    // If there is no parent path (i.e., we are at the root), don't navigate further
    if (parentPath === "") {
        parentPath = "/";
    }

    // Fetch the contents of the parent directory
    fetchFolderContents(parentPath);
});


$("#top-rename").click(function() {
   let selectedItem = $("#select_path").val();
   let selectedtype = $("#select_type").val();
   let selectedItemname = $("#select_file_name").val();
    if (selectedItem) {
      openactionPopup("Rename",selectedItemname,selectedItem);
    } else {
        alert("No file or folder selected.");
    }
});

$("#top-copy").click(function() {
   let selectedItem = $("#select_path").val();
   let selectedtype = $("#select_type").val();
   let selectedItemname = $("#select_file_name").val();
    if (isSelectionValid()) {
      openactionPopup("Copy",selectedItemname,selectedItem);
    } else {
        alert("No file or folder selected.");
    }
});

$("#top-move").click(function() {
   let selectedItem = $("#select_path").val();
   let selectedtype = $("#select_type").val();
   let selectedItemname = $("#select_file_name").val();
    if (isSelectionValid()) {
      openactionPopup("Move",selectedItemname,selectedItem);
    } else {
        alert("No file or folder selected.");
    }
});

$("#top-delete").click(function() {
   let selectedItem = $("#select_path").val();
   let selectedtype = $("#select_type").val();
   let selectedItemname = $("#select_file_name").val();
    if (isSelectionValid()) {
      openactionPopup("Delete",selectedItemname,selectedItem);
    } else {
		
        //alert("No file or folder selected.");
    }
});

$("#top-unzip").click(function() {
    let selectedItemext = ($("#select_ext").val() || '').toLowerCase();
    let selectedItem = $("#select_path").val();
    let selectedItemname = $("#select_file_name").val();

    if (!selectedItem) {
        const sel = document.querySelector('#file-list .item[aria-selected="true"]');
        if (sel) {
            selectedItem = sel.dataset.path;
            selectedItemname = sel.dataset.name;
            selectedItemext = (sel.dataset.ext || '').toLowerCase();
        }
    }

    const isArchive = selectedItemext === '.zip' || selectedItemext === '.gz' || 
                      selectedItemext === '.tgz' || selectedItemext === '.tar' ||
                      (selectedItemname && /\.(zip|tar\.gz|tgz|gz|tar)$/i.test(selectedItemname));

    if (isArchive && selectedItem) {
        openactionPopup("Unzip", selectedItemname, selectedItem);
    } else {
        alert("Please select a compressed archive (.zip, .tar.gz, .tgz, .gz) to extract.");
    }
});
$("#top-compress").click(function() {
let selectedItemext = $("#select_ext").val();
   let selectedItem = $("#select_path").val();
   let selectedtype = $("#select_type").val();
   let selectedItemname = $("#select_file_name").val();
    if (isSelectionValid()) {
      openactionPopup("Compress",selectedItemname,selectedItem);
    } else {
        alert("No Zip file selected.");
    }
});

$("#fix-permission").click(function() {
let selectedItemext = $("#select_ext").val();
   let selectedItem = $("#select_path").val();
   let selectedtype = $("#select_type").val();
   let selectedItemname = $("#select_file_name").val();
    if (isSelectionValid()) {
      openactionPopup("Fix-Permission",selectedItemname,selectedItem);
    } else {
		let parentPath = $("#location").val();
        openactionPopup("Fix-Permission",parentPath,parentPath);
    }
});

$("#top-view").click(function() {
   let selectedItem = $("#select_path").val();
   let selectedtype = $("#select_type").val();
   let selectedItemname = $("#select_file_name").val();
    if (selectedItem && selectedtype=='file') {
        // Open the editor page in a new tab with the selected file path as a query parameter
        window.open( view+ `?file=${encodeURIComponent(selectedItem)}&view=1`, '_blank');
    } else {
        alert("No file selected for view.");
    }
});

$("#new-folder").click(function() {
    let selectedItem = $("#location").val();
  
   
      openactionPopup("New Folder","",selectedItem);
});

$("#new-file").click(function() {
   let selectedItem = $("#location").val();
  
   
      openactionPopup("New File","",selectedItem);
    
});
$("#top-download").click(function() {
   let selectedItem = $("#select_path").val();
   let selectedtype = $("#select_type").val();
   let selectedItemname = $("#select_file_name").val();
    if (selectedItem && selectedtype=='file') {
	   window.open(download_url+`?file=${encodeURIComponent(selectedItem)}`, '_blank');
    } else {
        alert("No file selected for view.");
    }
});



$("#top-permission").click(function() {
   let selectedItem = $("#select_path").val();
   let selectedtype = $("#select_type").val();
   let selectedItemname = $("#select_file_name").val();
   let selectedItemper = $("#select_permission").val();
    if (isSelectionValid()) {
      openactionPopup("Permission",selectedItemname,selectedItem);
	   setPermission(selectedItemper);
    } else {
        alert("No file or folder selected.");
    }
});
	
    });

function parseSizeToBytes(sizeStr) {
    const units = { B: 1, KB: 1024, MB: 1024*1024, GB: 1024*1024*1024 };
    const match = sizeStr.match(/([\d.]+)\s*(Bytes|KB|MB|GB)/i);
    if (!match) return 0;
    const value = parseFloat(match[1]);
    const unit = match[2].toUpperCase().replace("BYTES", "B");
    return value * (units[unit] || 1);
}
function sortBy(field, element) {
    if (currentSortField === field) {
        currentSortDirection = currentSortDirection === "asc" ? "desc" : "asc";
    } else {
        currentSortField = field;
        currentSortDirection = "asc";
    }

    // Update UI: remove active class and clear icons from all sort buttons
    document.querySelectorAll(".sort-btn, .file-header p").forEach(btn => {
        btn.classList.remove("active");
        const icon = btn.querySelector(".sort-icon, i");
        if (icon) icon.textContent = "";
    });

    // Set active state and icon
    element.classList.add("active");
    const icon = currentSortDirection === "asc" ? "arrow_upward" : "arrow_downward";
    const iconEl = element.querySelector(".sort-icon, i");
    if (iconEl) {
        iconEl.textContent = icon;
    }

    // Call sorting function
    sortAndRenderEntries();
}


function fetchFolderContents(path = "") {
	$("#select_path").val("");
    $("#select_type").val("");
    $("#select_file_name").val("");
	unselectAll();
    currentPath = path;
    $("#location").val(currentPath);
	$("#empty_data").hide();
	$("#file-list").empty();
    $("#loading-container").show();

    $.ajax({
        url: file_folder_list_url,
        method: "GET",
        data: { directory: path },
        dataType: "json",
        success: function(response) {
            $("#file-list").empty();
			 
			$("#empty_data").hide();
            if (response.status === "success") {
				
               
                currentEntries = response.entries;
				if (!currentEntries || currentEntries.length === 0) {
                    $("#empty_data").text('This folder is empty');
                    $("#empty_data").show();
                }else{
				
                sortAndRenderEntries();
				}
            }
            $("#loading-container").hide();
        },
        error: function(error) {
            $("#loading-container").hide();
		
    $("#empty_data").text('Error fetching folder contents'); // set error text
    $("#empty_data").show(); 
        }
    });
}

function sortAndRenderEntries() {
    let sorted = [...currentEntries];

    // Only sort if a sort field is set
    if (currentSortField && currentSortDirection) {
        sorted.sort((a, b) => {
            // Keep directories on top
            if (a.is_dir !== b.is_dir) {
                return a.is_dir ? -1 : 1;
            }
            let valA, valB;

            if (currentSortField === "name") {
                valA = (a.name || "").toLowerCase();
                valB = (b.name || "").toLowerCase();
            } else if (currentSortField === "size") {
                valA = parseSizeToBytes(a.size || "0 Bytes");
                valB = parseSizeToBytes(b.size || "0 Bytes");
            } else if (currentSortField === "modified") {
                valA = new Date(a.modified_time || 0).getTime();
                valB = new Date(b.modified_time || 0).getTime();
            }

            if (valA < valB) return currentSortDirection === "asc" ? -1 : 1;
            if (valA > valB) return currentSortDirection === "asc" ? 1 : -1;
            return 0;
        });
    }

    $("#file-list").empty();

    sorted.forEach(function(entry) {
        const icon = entry.icon;
        const itemType = entry.is_dir ? "folder" : "file";

        const lastModifiedISO = entry.modified_time ? new Date(entry.modified_time).toISOString() : "";
        const lastModifiedDisplay = entry.modified_time ? new Date(entry.modified_time).toLocaleString() : "Unknown";
        const sizeInBytes = parseSizeToBytes(entry.size || "0 Bytes");

        const itemHTML = `
            <div class="item" id="${itemType}" data-path="${entry.path}" role="button" tabindex="0" draggable="true" 
                data-dir="${entry.is_dir}" data-type="${itemType}" data-name="${entry.name}" 
                aria-label="${entry.name}" aria-selected="false" data-ext=".${entry.extension}" data-permission="${entry.permissions}">
                <div><img src="${icon}" alt="${entry.name} Icon" /></div>
                <div>
                    <p class="name">${entry.name}</p>
                    <p class="size" data-order="${sizeInBytes}">${entry.size}</p>
                    <p class="modified"><time datetime="${lastModifiedISO}">${lastModifiedDisplay}</time></p>
                    <p class="permission">${entry.permissions}</p>
                </div>
            </div>
        `;
        $("#file-list").append(itemHTML);
    });

    attachClickEventListeners();
}


document.querySelectorAll('.upload-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        // Remove active class from all tabs
        document.querySelectorAll('.upload-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        // Toggle sections
        const selectedTab = tab.getAttribute('data-tab');
        document.getElementById('drop-zone').style.display = (selectedTab === 'file') ? 'flex' : 'none';
        document.getElementById('upload-url-section').style.display = (selectedTab === 'url') ? 'block' : 'none';
        document.getElementById('fup').style.display = (selectedTab === 'file') ? 'flex' : 'none';
        document.getElementById('furl').style.display = (selectedTab === 'url') ? 'flex' : 'none';
    });
});
 

function uploadFileFromUrl(fileUrl, targetPath) {
    const formData = new FormData();
    formData.append('file_url', fileUrl);
    formData.append('target_name', targetPath);

    const progressBar = $('#prog .progress-bar');
    const progressPercentage = $('#prog .progress-percentage');
    const btn = $('#upload-button-url');

    progressBar.removeClass('complete failed').css('width', '0%');
    progressPercentage.text('0%');
    $('#prog').show();
    btn.prop('disabled', true).html('<i class="fa fa-circle-o-notch fa-spin" style="margin-right: 6px;"></i> Downloading...');

    let progress = 0;
    const interval = setInterval(() => {
        if (progress < 85) {
            progress += 5;
            progressBar.css('width', `${progress}%`);
            progressPercentage.text(`${progress}%`);
        }
    }, 250);

    $.ajax({
        url: upload_url_from_url,
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        headers: { "X-CSRFToken": csrfToken },
        success: function (response) {
            clearInterval(interval);
            btn.prop('disabled', false).html('Upload');
            progressBar.removeClass('failed').addClass('complete').css('width', '100%');
            progressPercentage.html('<span style="color: #10b981; font-weight: 600;"><i class="fa fa-check-circle"></i> Complete</span>');

            const path = targetPath || '/';
            fetchFolderContents(path);
        },
        error: function (xhr, status, error) {
            clearInterval(interval);
            btn.prop('disabled', false).html('Upload');
            progressBar.removeClass('complete').addClass('failed').css('width', '100%');
            progressPercentage.html('<span style="color: #ef4444; font-weight: 600;"><i class="fa fa-times-circle"></i> Failed</span>');
            console.error('Upload from URL failed:', error, status, xhr.responseText);
        }
    });
}

$('#upload-button-url').on('click', function () {
    const url = $('#url-input').val().trim();
    const targetPath = $("#location").val() || "/";  // assuming you want to reuse the folder input

    if (!url) {
        alert('Please enter a file URL to upload.');
        return;
    }

    uploadFileFromUrl(url, targetPath);
});


function isSelectionValid() {
  const selectedItem = $("#select_path").val();
  const selectedItems = getSelectedItems(); 	


  return (
    (selectedItem && selectedItem.length > 0) ||
    (Array.isArray(selectedItems) && selectedItems.length > 0)
  );
}
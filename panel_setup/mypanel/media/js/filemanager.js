function uploadFile(file, index) {
    let parentPath = $("#location").val();
    const formData = new FormData();
    formData.append('file', file);
    formData.append('target_name', parentPath);

    const fileId = `file-${file.name.replace(/[^a-zA-Z0-9]/g, '-')}`;
    const progressBar = $(`#${fileId} .progress-bar`);
    const progressPercentage = $(`#${fileId} .progress-percentage`);

    $.ajax({
        url: upload_url, // Django URL name for the upload view
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        headers: { "X-CSRFToken": csrfToken },
        xhr: function () {
            const xhr = new window.XMLHttpRequest();
            xhr.upload.addEventListener('progress', function (e) {
                if (e.lengthComputable) {
                    const percentComplete = Math.round((e.loaded / e.total) * 100);
                    progressBar.css('width', `${percentComplete}%`);
                    progressPercentage.text(`${percentComplete}%`);
                }
            }, false);
            return xhr;
        },
        success: function (response) {
            progressBar.css('background', 'green'); // Set to green on success
            progressPercentage.text('Complete'); // Optionally update text
			if (parentPath === "") {
                    parentPath = "/";
                }
                fetchFolderContents(parentPath);
        },
        error: function (xhr, status, error) {
            progressBar.addClass('failed'); // Set to red on failure
            progressPercentage.text('Failed'); // Optionally update text
            
            // Log full response
            console.log('Error:', error);
            console.log('Status:', status);
            console.log('Full Response:', xhr);
            console.log('Response Text:', xhr.responseText); // Server's response text
        }
    });
}


$('#upload-button').on('click', function () {
    const files = $('#file-input')[0].files;
    if (files.length === 0) {
        alert('Please select files to upload.');
        return;
    }

    Array.from(files).forEach((file, index) => {
        uploadFile(file, index);
    });
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
    var nav = document.querySelector('nav'); // Select the <nav> element
    var menuButton = document.querySelector('.menu-button'); // The button that toggles the sidebar

    // Check if the click was outside of the <nav> and the toggle button
    if (!nav.contains(event.target) && !menuButton.contains(event.target)) {
        // Remove 'active' class if it is present
        if (nav.classList.contains('active')) {
            nav.classList.remove('active');
        }
    }
});
function toggleSidebar() {
    var nav = document.querySelector('nav'); // Select the first <nav> element on the page

    // Toggle the 'active' class on the <nav> element
    nav.classList.toggle('active');
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
		cfName.style.display ='block';
        listContainer.style.display = 'none';
        //cfName.style.display = 'none';  // hide span
        return;
    }

    // Show both if items selected
    listContainer.style.display = 'block';
	if (selectedItems.length > 0) {
   cfName.style.display ='none';
	}
    // Clear and rebuild list
    listContainer.innerHTML = '';
    const ul = document.createElement('ul');
    ul.style.listStyle = 'none';
    ul.style.padding = 0;
    ul.style.margin = 0;

    selectedItems.forEach(path => {
        const li = document.createElement('li');
        li.textContent = path.replace(/^-/, ''); // remove leading -
        li.style.padding = '4px 0';
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

// Function to toggle selection of a specific item
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



function openactionPopup(type, selectedItemname,selectedItem) {
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
if(type=="Delete"){
del.style.display = 'flex';
all.style.display = 'none';
per.style.display = 'none';
}else if(type=="Permission"){
per.style.display = 'flex';
all.style.display = 'none';
del.style.display = 'none';
}
else if(type=="Fix-Permission"){
all.style.display = 'flex';
del.style.display = 'none';
per.style.display = 'none';
anames.style.display = 'none';

}
else{
 all.style.display = 'flex';
del.style.display = 'none';
per.style.display = 'none';
	}
	cfname.innerHTML = type+": "+selectedItemname;
	 actionpopup.style.display = 'flex';
	if(type=="Copy" || type=="Move" || type=="Unzip"){
	ahome.style.display = 'block';
	anames.value =$("#location").val();
	}else if(type=="Compress"){
	ahome.style.display = 'block';
	anames.value =$("#location").val()+'/'+selectedItemname+'.zip';
	}else{
	 anames.value = selectedItemname; 
	}
   
	apath.value = selectedItem;
	//type = type.replace(/-/g, " ");
    atitle.innerHTML = type; // Update the title
    aaction.innerHTML = type; // Update the action
	
}
function aclosePopup() {
del.style.display = 'none';
all.style.display = 'none';
per.style.display = 'none';
    actionpopup.style.display = 'none';
	 ahome.style.display = 'none';
	 anames.value = ''; // Clear input field
    atitle.innerHTML = '';
	aaction.innerHTML = '';
	apath.value = '';
	cfname.innerHTML = '';
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
    uploadModal.style.display = 'flex';
    filePreview.innerHTML = ''; // Clear previous file preview
}

function closeUploadModal() {
    uploadModal.style.display = 'none';
    fileInput.value = ''; // Clear selected files
    filePreview.innerHTML = ''; // Clear file preview
}

// Trigger open modal ONLY on button click
openUploadModalButton.addEventListener('click', openUploadModal);

// Close modal on cancel button click
cancelUploadButton.addEventListener('click', closeUploadModal);

// Trigger file input when select button is clicked
fileSelectButton.addEventListener('click', () => fileInput.click());

// Handle file selection from file input
fileInput.addEventListener('change', handleFiles);

// Function to handle files selected or dropped
function handleFiles(event) {
    const files = event.target.files || event.dataTransfer.files;

    // Update the file input with the selected or dropped files
    fileInput.files = files;

    const filePreview = document.getElementById('file-preview');
    filePreview.innerHTML = Array.from(files)
        .map(file => {
            const fileId = `file-${file.name.replace(/[^a-zA-Z0-9]/g, '-')}`;
            return `
                <div class="file-item" id="${fileId}">
                    <p>${file.name} (${formatFileSize(file.size)})</p>
                    <div class="progress-container">
                        <div class="progress-bar" style="width: 0%;"></div>
                        <span class="progress-percentage">0%</span>
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



// Upload Logic with Progress Bar Updates


// Function to handle the removal of a file preview
function removeFile(button) {
    const fileItem = button.parentElement; // Get the parent div of the button (the file item)
    fileItem.remove(); // Remove the file item from the DOM
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
let selectedItemext = $("#select_ext").val();
   let selectedItem = $("#select_path").val();
   let selectedtype = $("#select_type").val();
   let selectedItemname = $("#select_file_name").val();
    if (selectedItemext=='.zip' || selectedItemext=='.gz') {
      openactionPopup("Unzip",selectedItemname,selectedItem);
    } else {
        alert("No Zip file selected.");
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

    // Update UI: remove active class from all
    document.querySelectorAll(".sort-btn").forEach(btn => {
        btn.classList.remove("active");
        btn.querySelector("i").textContent = "";
    });

    // Set active state and icon
    element.classList.add("active");
    const icon = currentSortDirection === "asc" ? "arrow_upward" : "arrow_downward";
    element.querySelector("i").textContent = icon;

    // Call your sorting function
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
            let valA, valB;

            if (currentSortField === "name") {
                valA = a.name.toLowerCase();
                valB = b.name.toLowerCase();
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
        document.getElementById('drop-zone').style.display = (selectedTab === 'file') ? 'block' : 'none';
        document.getElementById('upload-url-section').style.display = (selectedTab === 'url') ? 'block' : 'none';
		document.getElementById('fup').style.display = (selectedTab === 'file') ? 'block' : 'none';
        document.getElementById('furl').style.display = (selectedTab === 'url') ? 'block' : 'none';
    });
});
 

function uploadFileFromUrl(fileUrl, targetPath) {
    const formData = new FormData();
    formData.append('file_url', fileUrl);
    formData.append('target_name', targetPath);

    const progressBar = document.querySelector('#prog .progress-bar');
    const progressPercentage = document.querySelector('#prog .progress-percentage');
 progressBar.style.width = '0%';
    progressBar.style.background = ''; // Reset to default or empty
    progressBar.classList.remove('failed');
    progressPercentage.textContent = '0%';
    $.ajax({
        url: upload_url_from_url,
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        headers: { "X-CSRFToken": csrfToken },
        xhr: function () {
            const xhr = new window.XMLHttpRequest();
            xhr.upload.addEventListener('progress', () => {
                // No actual upload progress from client to server here because we send URL only
            }, false);
            return xhr;
        },
        beforeSend: function () {
            // Simulate progress to 80%
            let progress = 0;
            this.interval = setInterval(() => {
                if (progress < 80) {
                    progress += 5;
                    progressBar.style.width = `${progress}%`;
                    progressPercentage.textContent = `${progress}%`;
                }
            }, 200);
        },
        success: function (response) {
            clearInterval(this.interval);
            progressBar.style.width = '100%';
            progressBar.style.background = 'green';
            progressPercentage.textContent = 'Complete';

            const path = targetPath || '/';
            fetchFolderContents(path);
        },
        error: function (xhr, status, error) {
            clearInterval(this.interval);
            progressBar.classList.add('failed');
            progressBar.style.width = '100%';
            progressPercentage.textContent = 'Failed';
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
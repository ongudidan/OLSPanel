function reloadPageWithUrl(url) {
	const inputElement = document.getElementById('path');
    
    // Get the value of the input field
    const inputValue = inputElement.value;
    window.location.href = baseUrl + phpEditorUrl + "?file=" + encodeURIComponent(inputValue); // Safely encode the URL
}
	
	
        const editor = ace.edit("editor");
        editor.setTheme("ace/theme/chrome"); // You can change the theme
        editor.session.setMode("ace/mode/"+ext); // Set the mode to PHP
        editor.setOptions({
    fontSize: "13px",  // Default font size
    wrap: true         // Enable word wrapping
});
//editor.setValue(contents, -1);
editor.selection.moveCursorTo(0, 0); 
editor.focus();
      let isSearchVisible = false; // State to track visibility
let searchInitialized = false; // State to track if a search has been performed



// Automatically perform search on input
document.getElementById('search-input').addEventListener('input', function() {
    const needle = this.value; // Get the current input value
    
    if (needle) {
        editor.find(needle, {
            backwards: false,
            wrap: false,
            caseSensitive: false,
            wholeWord: false,
            regExp: false
        });
        searchInitialized = true; // Mark search as initialized
        document.getElementById('find-next').disabled = false; // Enable buttons
        document.getElementById('find-prev').disabled = false; // Enable buttons
    } else {
        // If the input is empty, disable the buttons
        searchInitialized = false;
        document.getElementById('find-next').disabled = true;
        document.getElementById('find-prev').disabled = true;
    }
});

document.getElementById('find-next').onclick = function() {
    if (searchInitialized) {
        editor.findNext();
    }
};

document.getElementById('find-prev').onclick = function() {
    if (searchInitialized) {
        editor.findPrevious();
    }
};

// Highlight all occurrences when clicking the "All" button
document.getElementById('find-all').onclick = function() {
    const needle = document.getElementById('search-input').value; // Get the current input value
    if (needle) {
        editor.findAll(needle, {
            backwards: false,
            wrap: true,
            caseSensitive: false,
            wholeWord: false,
            regExp: false
        });
        // Optionally, update the counter to show how many results were found
        const foundCount = editor.getFoundCount(); // Assuming getFoundCount() method returns the number of matches
        document.querySelector('.ace_search_counter').textContent = `${foundCount} found`;
    }
};
		

		
		
		
var wrapEnabled = false;		
function toolbarActions(action) {
    switch(action) {
        case 'goto':
            goToLine();
            break;
        case 'undo':
            editor.undo();
            break;
        case 'redo':
            editor.redo();
            break;
        case 'linewrap':
              wrapEnabled = !wrapEnabled; // flip state
            editor.session.setUseWrapMode(wrapEnabled);
            if (wrapEnabled) {
                editor.session.setWrapLimitRange(80, 80);
            }
            break;
  
        default:
            console.warn(`Unknown action: ${action}`);
    }
}
 	
function goToLine() {
    const totalLines = editor.session.getLength();
    let line = prompt(`Enter line number (1-${totalLines}):`, "1");
    
    if (line !== null) { // If user didn't cancel
        line = parseInt(line, 10);
        if (!isNaN(line) && line >= 1 && line <= totalLines) {
            editor.scrollToLine(line, true, true, function () {});
            editor.gotoLine(line, 0, true);
            editor.focus();
        } else {
            alert("Invalid line number.");
        }
    }
}

function setFontSize() {
    const fontSize = document.getElementById('ddlFontSizes').value;  // Get the selected font size
    editor.setFontSize(fontSize + "px");  // Apply the font size to the editor
	saveSettings(fontSize);
}

// Attach the change event to the dropdown
document.getElementById('ddlFontSizes').addEventListener('change', setFontSize);

// Optionally, set a default font size when the page loads
window.onload = function() {
    const defaultFontSize = font_size;  // Default font size (can be customized)
    document.getElementById('ddlFontSizes').value = defaultFontSize;  // Set the default value in the dropdown
    editor.setFontSize(defaultFontSize + "px");  // Apply the default font size
};   

function toggleSearch() {
    var searchBoxVisible = false;
    if (!searchBoxVisible) {
        //searchContainer.style.display = "block";
		editor.execCommand("find");
    } else {
		editor.searchBox.hide();
        //searchContainer.style.display = "none";
    }
	searchBoxVisible = !searchBoxVisible; 
}

  document.addEventListener("DOMContentLoaded", function() {
        const saveButton = document.getElementById('sform_submit');
		 const responseDisplay = document.getElementById('responseContainer');
        const alertContainer = document.getElementById('alertContainer');
        const messageDisplay = document.getElementById('message');
		
        saveButton.addEventListener('click', function() {
            // Display saving message
            responseDisplay.style.display = 'inline-block';

            const content = editor.getValue();

            const inputElement = document.getElementById('path');
			const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value; // Get the CSRF token

    
    // Get the value of the input field
    const inputValue = inputElement.value;
            // Use fetch to send a POST request to save the file content
            fetch(joinUrl(baseUrl, phpEditorUrl) + "?file=" + inputValue, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken,
					'X-Requested-With': 'XMLHttpRequest'
                },
                body: new URLSearchParams({
                    'content': content
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok: ' + response.statusText);
                }
                return response.text(); // Return response as text
            })
            .then(data => {
                console.log('Response:', data);
                responseDisplay.style.display = 'none'; // Hide the saving message

                if (data.includes('success')) {
				 notify.addNotification({
          type: "success",
          title: "Success!",
          message: "File saved!"
      });
                   
                   //alertContainer.className = "alert alert-success alert-dismissible fade show";
                  //  messageDisplay.innerText = data; // Displaying success message
                } else {
                   notify.addNotification({
          type: "error",
          title: "Error!",
          message: "Failed"+ error.message
        }); 
                }

                alertContainer.style.display = "block"; // Show the alert

               
            })
            .catch(error => {
                console.error('Error:', error);
				
				
               
            });
        });
    });

 function closeTab() {
            // This will close the current tab
            window.close();
        }



function saveSettings(font_size) {
	const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value;
    const requestData = {
        font_size: font_size
    };

    fetch(saveUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: new URLSearchParams(requestData)  // this serializes it correctly
    })
    .then(response => response.json())
    .then(data => {
       // console.log('Settings saved:', data);
        // Optionally show a success message
    })
    .catch(error => {
      //  console.error('Error saving settings:', error);
        // Optionally show an error message
    });
}

function joinUrl(base, path) {
    return base.replace(/\/+$/, '') + '/' + path.replace(/^\/+/, '');
}
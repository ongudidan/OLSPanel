sub print_logs {
    my ($options_html) = @_;  # pass only options HTML for clarity

    print <<"HTML";
<div class="ufw-card" style="margin-top: 6px;">
    <div class="ufw-card-header" style="flex-wrap: wrap; gap: 8px;">
        <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
            <i class="mdi mdi-text-box-search-outline text-brand"></i>
            <select id="CSFlognum" name="lognum" class="ufw-input ufw-input-inline" onchange="CSFrefreshtimer()" style="width: 220px !important; font-size: 11px;">
                $options_html
            </select>
            <span style="font-size: 11px; color: #64748b; font-weight: 600;">Lines:</span>
            <input type="text" id="CSFlines" value="100" class="ufw-input ufw-input-inline" style="width: 60px !important; text-align: center;">
            <button class="btn-modern btn-brand" onclick="CSFrefreshtimer()">
                <i class="mdi mdi-refresh"></i> Refresh
            </button>
        </div>
        
        <div style="display: flex; align-items: center; gap: 6px;">
            <span style="font-size: 11px; color: #64748b;">Next in: <strong id="CSFtimer" style="color: #059669;">4</strong>s</span>
            <button class="btn-modern btn-secondary-modern" id="CSFpauseID" onclick="CSFpausetimer()">Pause</button>
            <span id="CSFrefreshing" style="display: none; font-size: 11px; color: #0284c7;"><i class="mdi mdi-loading mdi-spin"></i></span>
            <div style="display: flex; gap: 2px; margin-left: 6px;">
                <button class="btn-modern btn-secondary-modern" id="fontminus-btn" style="padding: 3px 7px;"><i class="mdi mdi-format-font-size-decrease"></i></button>
                <button class="btn-modern btn-secondary-modern" id="fontplus-btn" style="padding: 3px 7px;"><i class="mdi mdi-format-font-size-increase"></i></button>
            </div>
            <button class="btn-modern btn-secondary-modern" onclick="window.history.back();" style="margin-left: 8px;">
                <i class="mdi mdi-arrow-left"></i> Return
            </button>
        </div>
    </div>
    
    <div style="padding: 10px; background: #0f172a;">
        <pre class="terminal-box" id="CSFajax" style="margin: 0; min-height: 400px; max-height: 650px; border: none; background: transparent; font-size: 11px;">&lt;---- /usr/local/lsws/logs/access.log is currently empty ----&gt;</pre>
    </div>
    
    <div style="padding: 8px 12px; background: #f8fafc; border-top: 1px solid #e2e8f0; display: flex; justify-content: flex-end;">
        <button class="btn-modern btn-secondary-modern" onclick="window.history.back();">
            <i class="mdi mdi-arrow-left"></i> Return to Firewall Console
        </button>
    </div>
</div>
HTML

    print <<'HTML';
<script>
var CSFscript = '';
var CSFcountval = 6;
var CSFlineval = 100;
var CSFcounter;
var CSFcount = 1;
var CSFpause = 0;
var CSFfrombot = 120;
var CSFfromright = 10;
var CSFsettimer = 0;
var CSFheight = 0;
var CSFwidth = 0;
var CSFajaxHTTP = CSFcreateRequestObject();

function CSFcreateRequestObject() {
	var CSFajaxRequest;
	if (window.XMLHttpRequest) {
		CSFajaxRequest = new XMLHttpRequest();
	}
	else if (window.ActiveXObject) {
		CSFajaxRequest = new ActiveXObject("Microsoft.XMLHTTP");
	}
	else {
		alert('There was a problem creating the XMLHttpRequest object in your browser');
		CSFajaxRequest = '';
	}
	return CSFajaxRequest;
}

function CSFsendRequest(url) {
	var now = new Date();
	CSFajaxHTTP.open('get', url + '&nocache=' + now.getTime());
	CSFajaxHTTP.onreadystatechange = CSFhandleResponse;
	CSFajaxHTTP.send();
	var ref = document.getElementById("CSFrefreshing");
	if (ref) ref.style.display = "inline";
} 

function CSFhandleResponse() {
	if(CSFajaxHTTP.readyState == 4 && CSFajaxHTTP.status == 200){
		if(CSFajaxHTTP.responseText) {
			var CSFobj = document.getElementById("CSFajax");
			CSFobj.innerHTML = CSFajaxHTTP.responseText;
			waitForElement("CSFajax",function(){
				CSFobj.scrollTop = CSFobj.scrollHeight;
			});
			var ref = document.getElementById("CSFrefreshing");
			if (ref) ref.style.display = "none";
			if (CSFsettimer) {CSFcounter = setInterval(CSFtimer, 1000);}
		}
	}
}

function waitForElement(elementId, callBack){
	window.setTimeout(function(){
		var element = document.getElementById(elementId);
		if(element){
			callBack(elementId, element);
		}else{
			waitForElement(elementId, callBack);
		}
	},500);
}

function CSFtimer() {
	if (!CSFpause) {
		if (CSFcount == 0) {
			var CSFlineobj = document.getElementById("CSFlines");
			if (CSFlineobj) {
				if (CSFlineobj.value > 0) {
					CSFlineval = CSFlineobj.value;
				} else {
					CSFlineobj.value = CSFlineval;
				}
			}
			var CSFlogobj = document.getElementById("CSFlognum");
			var CSFlognum = '';
			if (CSFlogobj) {
				CSFlognum = '&lognum=' + CSFlogobj.options[CSFlogobj.selectedIndex].value;
			}
			CSFsendRequest(CSFscript + '&lines=' + CSFlineval + CSFlognum);
			CSFcount = CSFcountval;
		}
		var timerEl = document.getElementById("CSFtimer");
		if (timerEl) timerEl.innerHTML = CSFcount;
		CSFcount--;
	}
	if (!CSFsettimer) {
		CSFsettimer = 1;
		CSFcounter = setInterval(CSFtimer, 1000);
	}
}

function CSFpausetimer() {
	if (CSFpause) {
		CSFpause = 0;
		document.getElementById("CSFpauseID").innerHTML = "Pause";
	}
	else {
		CSFpause = 1;
		document.getElementById("CSFpauseID").innerHTML = "Continue";
	}
}

function CSFrefreshtimer() {
	var pause = CSFpause;
	CSFcount = 1;
	CSFpause = 0;
	CSFtimer();
	CSFpause = pause;
	CSFcount = CSFcountval - 1;
	var timerEl = document.getElementById("CSFtimer");
	if (timerEl) timerEl.innerHTML = CSFcount;
}

CSFfrombot = 120;
CSFfromright = 10;
CSFscript = '/whm/iframe/?action=logtailcmd';
CSFtimer();

var myFont = 11;
$("#fontplus-btn").on('click', function () {
	myFont++;
	if (myFont > 16) {myFont = 16;}
	$('#CSFajax').css("font-size", myFont + "px");
});
$("#fontminus-btn").on('click', function () {
	myFont--;
	if (myFont < 10) {myFont = 10;}
	$('#CSFajax').css("font-size", myFont + "px");
});
</script>
HTML
}
1;
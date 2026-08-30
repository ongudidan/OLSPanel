# main.pl

sub print_main {
    my () = @_;

    my $ufw_status = get_ufw_status();   

    if ($ufw_status eq 'active') {
        print <<'HTML';
<div class="status-banner status-active">
    <div style="display: flex; align-items: center;">
        <span class="pulse-indicator pulse-active"></span>
        <span>Firewall Status: <strong style="color: #047857;">Enabled &amp; Active</strong></span>
    </div>
    <span style="font-size: 11px; color: #059669; font-weight: 500;">Packet filtering rules active</span>
</div>
HTML
    } else {
        print <<'HTML';
<div class="status-banner status-inactive">
    <div style="display: flex; align-items: center;">
        <span class="pulse-indicator pulse-inactive"></span>
        <span>Firewall Status: <strong style="color: #be123c;">Disabled &amp; Inactive</strong></span>
    </div>
    <form action="" method="post" style="margin: 0;">
        <input type="hidden" name="action" value="ufw_enable">
        <button type="submit" class="btn-modern btn-brand" style="padding: 3px 9px; font-size: 11px;">
            <i class="mdi mdi-power"></i> Enable Firewall
        </button>
    </form>
</div>
HTML
    }

    print <<"END_HTML";
<div class="normalcontainer">
<ul class="nav nav-tabs" id="myTabs">
    <li class="active"><a data-toggle="tab" href="#ufw"><i class="mdi mdi-shield-outline"></i> UFW Management</a></li>
    <li><a data-toggle="tab" href="#auto_block"><i class="mdi mdi-shield-account-outline"></i> Brute Force Protection</a></li>
    <li><a href="javascript:void(0);" onclick="try{window.parent.switchUfwTab('blocked');}catch(e){}"><i class="mdi mdi-account-cancel-outline" style="color: #e11d48;"></i> Blocked IP Addresses</a></li>
    <li><a data-toggle="tab" href="#other"><i class="mdi mdi-text-box-outline"></i> System Logs &amp; Other</a></li>
</ul>

<div class="tab-content">

<!-- UFW Management Tab -->
<div id="ufw" class="tab-pane active">

    <!-- Section 1: System Control -->
    <div class="ufw-card">
        <div class="ufw-card-header">
            <span><i class="mdi mdi-tune text-brand"></i> UFW Status &amp; Service Control</span>
            <span style="font-size: 10px; color: #94a3b8; font-weight: normal;">Daemon Commands</span>
        </div>
        <table class="table-ufw">
            <tbody>
                <tr>
                    <td style="width: 170px;">
                        <form action="" method="post" style="margin:0;">
                            <button name="action" value="logtail" type="submit" class="btn-modern btn-info-modern" style="width: 100%;">
                                <i class="mdi mdi-file-document-outline"></i> Watch Logs
                            </button>
                        </form>
                    </td>
                    <td>Display real-time UFW packet drop and access events</td>
                </tr>
                <tr>
                    <td>
                        <form action="" method="post" style="margin:0;">
                            <button name="action" value="ufw_enable" type="submit" class="btn-modern btn-brand" style="width: 100%;">
                                <i class="mdi mdi-play"></i> Enable UFW
                            </button>
                        </form>
                    </td>
                    <td>Activate firewall packet filtering protection on all network interfaces</td>
                </tr>
                <tr>
                    <td>
                        <form action="" method="post" style="margin:0;">
                            <button name="action" value="ufw_disable" type="submit" class="btn-modern btn-warning-modern" style="width: 100%;">
                                <i class="mdi mdi-pause"></i> Disable UFW
                            </button>
                        </form>
                    </td>
                    <td>Temporarily bypass firewall packet inspection (WARNING: Removes inbound protection)</td>
                </tr>
                <tr>
                    <td>
                        <form action="" method="post" style="margin:0;">
                            <button name="action" value="ufw_restart" type="submit" class="btn-modern btn-danger-modern" style="width: 100%;">
                                <i class="mdi mdi-refresh"></i> Restart UFW
                            </button>
                        </form>
                    </td>
                    <td>Reload all active firewall profiles and re-initialize iptables rules</td>
                </tr>
                <tr>
                    <td>
                        <form action="" method="post" style="margin:0;">
                            <button name="action" value="ufw_list_rules_table" type="submit" class="btn-modern btn-secondary-modern" style="width: 100%;">
                                <i class="mdi mdi-table"></i> Rules (Table)
                            </button>
                        </form>
                    </td>
                    <td>Inspect all active rules in structured tabular format with one-click deletion</td>
                </tr>
                <tr>
                    <td>
                        <form action="" method="post" style="margin:0;">
                            <button name="action" value="ufw_list_rules" type="submit" class="btn-modern btn-secondary-modern" style="width: 100%;">
                                <i class="mdi mdi-format-list-numbered"></i> Rules (Plain)
                            </button>
                        </form>
                    </td>
                    <td>Display raw numbered rules straight from standard system crontab/cli</td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- Section 2: IP Address Management -->
    <div class="ufw-card">
        <div class="ufw-card-header">
            <span><i class="mdi mdi-ip-network-outline text-brand"></i> IP Address Management</span>
            <span style="font-size: 10px; color: #94a3b8; font-weight: normal;">CIDR / Single Host</span>
        </div>
        <table class="table-ufw">
            <tbody>
                <tr>
                    <td style="width: 170px; vertical-align: top;">
                        <button onclick="\$('#ufw_allow_ip_form').submit();" class="btn-modern btn-brand" style="width: 100%;">
                            <i class="mdi mdi-check-circle-outline"></i> Allow IP
                        </button>
                    </td>
                    <td>
                        <form action="" method="post" id="ufw_allow_ip_form" style="margin:0; display: flex; flex-direction: column; gap: 6px;">
                            <input type="hidden" name="action" value="ufw_allow_ip">
                            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                <label style="font-size: 11px; font-weight: 600; color: #475569; width: 100px; margin: 0;">IP Address:</label>
                                <input type="text" name="ip" placeholder="192.168.1.100 or 10.0.0.0/24" class="ufw-input" required>
                            </div>
                            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                <label style="font-size: 11px; font-weight: 600; color: #475569; width: 100px; margin: 0;">Comment:</label>
                                <input type="text" name="comment" placeholder="Optional identifier (e.g. Office VPN)" class="ufw-input">
                            </div>
                        </form>
                    </td>
                </tr>
                <tr>
                    <td style="width: 170px; vertical-align: top;">
                        <button onclick="\$('#ufw_deny_ip_form').submit();" class="btn-modern btn-danger-modern" style="width: 100%;">
                            <i class="mdi mdi-cancel"></i> Deny IP
                        </button>
                    </td>
                    <td>
                        <form action="" method="post" id="ufw_deny_ip_form" style="margin:0; display: flex; flex-direction: column; gap: 6px;">
                            <input type="hidden" name="action" value="ufw_deny_ip">
                            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                <label style="font-size: 11px; font-weight: 600; color: #475569; width: 100px; margin: 0;">IP Address:</label>
                                <input type="text" name="ip" placeholder="1.2.3.4" class="ufw-input" required>
                            </div>
                            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                <label style="font-size: 11px; font-weight: 600; color: #475569; width: 100px; margin: 0;">Comment:</label>
                                <input type="text" name="comment" placeholder="Optional reason (e.g. Abuse reported)" class="ufw-input">
                            </div>
                        </form>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- Section 3: Port Management -->
    <div class="ufw-card">
        <div class="ufw-card-header">
            <span><i class="mdi mdi-lan-connect text-brand"></i> Port Management</span>
            <span style="font-size: 10px; color: #94a3b8; font-weight: normal;">TCP / UDP Rules</span>
        </div>
        <table class="table-ufw">
            <tbody>
                <tr>
                    <td style="width: 170px; vertical-align: top;">
                        <button onclick="\$('#ufw_allow_port_form').submit();" class="btn-modern btn-brand" style="width: 100%;">
                            <i class="mdi mdi-check-network-outline"></i> Allow Port
                        </button>
                    </td>
                    <td>
                        <form action="" method="post" id="ufw_allow_port_form" style="margin:0; display: flex; flex-direction: column; gap: 6px;">
                            <input type="hidden" name="action" value="ufw_allow_port">
                            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                <label style="font-size: 11px; font-weight: 600; color: #475569; width: 60px; margin: 0;">Port:</label>
                                <input type="text" name="port" id="allow_port_input" placeholder="80" class="ufw-input ufw-input-inline" style="width: 110px !important;" required>
                                <label style="font-size: 11px; font-weight: 600; color: #475569; margin: 0 4px 0 10px;">Protocol:</label>
                                <select name="protocol" class="ufw-input ufw-input-inline" style="width: 90px !important;">
                                    <option value="tcp">TCP</option>
                                    <option value="udp">UDP</option>
                                </select>
                            </div>
                            <div class="port-quick-fill">
                                <span style="font-size: 10px; color: #64748b; font-weight: 600;">Quick Fill:</span>
                                <button type="button" class="port-chip" onclick="fillPort('allow_port_input', '80')">HTTP 80</button>
                                <button type="button" class="port-chip" onclick="fillPort('allow_port_input', '443')">HTTPS 443</button>
                                <button type="button" class="port-chip" onclick="fillPort('allow_port_input', '22')">SSH 22</button>
                                <button type="button" class="port-chip" onclick="fillPort('allow_port_input', '21')">FTP 21</button>
                                <button type="button" class="port-chip" onclick="fillPort('allow_port_input', '25')">SMTP 25</button>
                                <button type="button" class="port-chip" onclick="fillPort('allow_port_input', '53')">DNS 53</button>
                                <button type="button" class="port-chip" onclick="fillPort('allow_port_input', '3306')">MySQL 3306</button>
                            </div>
                        </form>
                    </td>
                </tr>
                <tr>
                    <td style="width: 170px; vertical-align: top;">
                        <button onclick="\$('#ufw_deny_port_form').submit();" class="btn-modern btn-danger-modern" style="width: 100%;">
                            <i class="mdi mdi-close-network-outline"></i> Deny Port
                        </button>
                    </td>
                    <td>
                        <form action="" method="post" id="ufw_deny_port_form" style="margin:0; display: flex; flex-direction: column; gap: 6px;">
                            <input type="hidden" name="action" value="ufw_deny_port">
                            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                <label style="font-size: 11px; font-weight: 600; color: #475569; width: 60px; margin: 0;">Port:</label>
                                <input type="text" name="port" id="deny_port_input" placeholder="23" class="ufw-input ufw-input-inline" style="width: 110px !important;" required>
                                <label style="font-size: 11px; font-weight: 600; color: #475569; margin: 0 4px 0 10px;">Protocol:</label>
                                <select name="protocol" class="ufw-input ufw-input-inline" style="width: 90px !important;">
                                    <option value="tcp">TCP</option>
                                    <option value="udp">UDP</option>
                                </select>
                            </div>
                            <div class="port-quick-fill">
                                <span style="font-size: 10px; color: #64748b; font-weight: 600;">Quick Fill:</span>
                                <button type="button" class="port-chip" onclick="fillPort('deny_port_input', '80')">HTTP 80</button>
                                <button type="button" class="port-chip" onclick="fillPort('deny_port_input', '443')">HTTPS 443</button>
                                <button type="button" class="port-chip" onclick="fillPort('deny_port_input', '22')">SSH 22</button>
                                <button type="button" class="port-chip" onclick="fillPort('deny_port_input', '21')">FTP 21</button>
                                <button type="button" class="port-chip" onclick="fillPort('deny_port_input', '25')">SMTP 25</button>
                                <button type="button" class="port-chip" onclick="fillPort('deny_port_input', '53')">DNS 53</button>
                                <button type="button" class="port-chip" onclick="fillPort('deny_port_input', '3306')">MySQL 3306</button>
                            </div>
                        </form>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- Section 4: Search and Rule Removal -->
    <div class="ufw-card">
        <div class="ufw-card-header">
            <span><i class="mdi mdi-magnify text-brand"></i> Search &amp; Rule Removal</span>
            <span style="font-size: 10px; color: #94a3b8; font-weight: normal;">Lookup / Delete by Index</span>
        </div>
        <table class="table-ufw">
            <tbody>
                <tr>
                    <td style="width: 170px;">
                        <button onclick="\$('#ufw_search_form').submit();" class="btn-modern btn-info-modern" style="width: 100%;">
                            <i class="mdi mdi-magnify"></i> Search Rules
                        </button>
                    </td>
                    <td>
                        <form action="" method="post" id="ufw_search_form" style="margin:0; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                            <input type="hidden" name="action" value="ufw_search">
                            <label style="font-size: 11px; font-weight: 600; color: #475569; margin: 0;">Pattern / IP / Port:</label>
                            <input type="text" name="search_term" placeholder="e.g. 22 or 192.168" class="ufw-input" required>
                        </form>
                    </td>
                </tr>
                <tr>
                    <td style="width: 170px;">
                        <button onclick="\$('#ufw_remove_rule_form').submit();" class="btn-modern btn-warning-modern" style="width: 100%;">
                            <i class="mdi mdi-delete-outline"></i> Remove Rule
                        </button>
                    </td>
                    <td>
                        <form action="" method="post" id="ufw_remove_rule_form" style="margin:0; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                            <input type="hidden" name="action" value="ufw_remove_rule">
                            <label style="font-size: 11px; font-weight: 600; color: #475569; margin: 0;">Rule Index #:</label>
                            <input type="text" name="rule_number" placeholder="1" class="ufw-input ufw-input-inline" style="width: 80px !important;" required>
                            <span style="font-size: 10px; color: #94a3b8;">(Inspect rules via &quot;Rules (Table)&quot; above to find rule numbers)</span>
                        </form>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>

</div>

<!-- Brute Force Protection Tab -->
<div id="auto_block" class="tab-pane">
    <div class="ufw-card" style="margin-bottom: 14px;">
        <div class="ufw-card-header">
            <span><i class="mdi mdi-shield-lock-outline text-brand"></i> Automated Brute-Force Intrusion Prevention</span>
            <span style="font-size: 10px; color: #94a3b8; font-weight: normal;">Log Inspection Daemons</span>
        </div>
        <div class="ufw-card-body" style="background: #f8fafc; font-size: 12px; color: #475569;">
            Configure real-time log monitoring triggers to automatically isolate and block repeated failed login attempts per protocol.
        </div>
    </div>
END_HTML

    conf_list_head();
    print <<"END_HTML";
    <div class="tab-content" style="margin-top: 10px;">
END_HTML

    conf_list();

    print <<"END_HTML";
    </div>
</div>

<!-- Other / Logs Tab -->
<div id="other" class="tab-pane">
    <div class="ufw-card">
        <div class="ufw-card-header">
            <span><i class="mdi mdi-text-box-search-outline text-brand"></i> Firewall Logs &amp; Diagnostics</span>
            <span style="font-size: 10px; color: #94a3b8; font-weight: normal;">Audit Trail</span>
        </div>
        <table class="table-ufw">
            <tbody>
                <tr>
                    <td style="width: 170px;">
                        <form action="" method="post" style="margin: 0;">
                            <button name="action" value="logtail" type="submit" class="btn-modern btn-info-modern" style="width: 100%;">
                                <i class="mdi mdi-file-eye-outline"></i> View Full Log
                            </button>
                        </form>
                    </td>
                    <td>Stream live UFW kernel and OpenLiteSpeed access/error logs with auto-refresh</td>
                </tr>
            </tbody>
        </table>
    </div>
</div>

</div>
</div>

<script>
window.fillIP = function(fieldName, ip) {
    var el = document.getElementById(fieldName) || document.querySelector('input[name="' + fieldName + '"]');
    if (el) {
        el.value = ip;
        \$(el).trigger('input');
    }
};

window.fillPort = function(elementId, port) {
    var el = document.getElementById(elementId) || document.querySelector('input[name="' + elementId + '"]');
    if (el) {
        el.value = port;
        \$(el).trigger('input');
    }
};
</script>
END_HTML
}
1;

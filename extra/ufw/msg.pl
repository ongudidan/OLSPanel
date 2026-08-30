sub print_msg {
    my ($msg) = @_;

    print <<"HTML";
<div class="ufw-card" style="margin-top: 6px;">
    <div class="ufw-card-header">
        <span><i class="mdi mdi-console-line text-brand"></i> Execution Output</span>
        <button class="btn-modern btn-secondary-modern" onclick="window.history.back();" style="padding: 2px 8px; font-size: 11px;">
            <i class="mdi mdi-arrow-left"></i> Return
        </button>
    </div>
    <div class="ufw-card-body" style="padding: 10px; background: #0f172a;">
        <pre class="terminal-box" id="CSFajax" style="margin: 0; min-height: 280px; max-height: 600px; border: none; background: transparent;">$msg</pre>
    </div>
    <div style="padding: 8px 12px; background: #f8fafc; border-top: 1px solid #e2e8f0; display: flex; justify-content: flex-end;">
        <button class="btn-modern btn-secondary-modern" onclick="window.history.back();">
            <i class="mdi mdi-arrow-left"></i> Return to Firewall Console
        </button>
    </div>
</div>
HTML
}
1;
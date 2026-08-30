# header.pl

sub print_header {
    my ($result_msg, $bootstrapcss, $jqueryjs, $bootstrapjs, $images) = @_;

    print <<"END_HTML";
<!doctype html>
<html lang='en'>
<head>
    <title>UFW Firewall &amp; Security</title>
    <meta charset='utf-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1'>
    $bootstrapcss
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/\@mdi/font\@7.4.47/css/materialdesignicons.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <link href='$images/configserver.css?v=2' rel='stylesheet' type='text/css'>
    $jqueryjs
    $bootstrapjs
    <style>
        :root {
            --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            --font-mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            --brand-primary: #059669;
            --brand-hover: #047857;
            --brand-light: #ecfdf5;
        }
        body {
            font-family: var(--font-sans) !important;
            background-color: #ffffff !important;
            color: #1e293b !important;
            font-size: 13px !important;
            padding: 12px 14px !important;
            margin: 0 !important;
        }
        .container-fluid {
            padding: 0 !important;
            max-width: 100% !important;
        }
        
        /* Modern Tabs */
        .nav-tabs {
            border-bottom: 1px solid #e2e8f0 !important;
            margin-bottom: 14px !important;
            gap: 4px;
            display: flex;
        }
        .nav-tabs > li {
            margin-bottom: -1px;
        }
        .nav-tabs > li > a {
            border: 1px solid transparent !important;
            border-radius: 6px 6px 0 0 !important;
            padding: 7px 14px !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            color: #64748b !important;
            background: transparent !important;
            transition: all 0.15s ease !important;
        }
        .nav-tabs > li > a:hover {
            color: #0f172a !important;
            background: #f8fafc !important;
            border-color: #e2e8f0 #e2e8f0 transparent !important;
        }
        .nav-tabs > li.active > a,
        .nav-tabs > li.active > a:hover,
        .nav-tabs > li.active > a:focus {
            color: var(--brand-primary) !important;
            background: #ffffff !important;
            border-color: #e2e8f0 #e2e8f0 #ffffff !important;
            font-weight: 700 !important;
            border-top: 2px solid var(--brand-primary) !important;
        }

        /* Status Cards */
        .status-banner {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 14px;
            border-radius: 6px;
            margin-bottom: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        .status-active {
            background-color: #ecfdf5;
            border: 1px solid #a7f3d0;
            color: #065f46;
        }
        .status-inactive {
            background-color: #fff1f2;
            border: 1px solid #fecdd3;
            color: #9f1239;
        }
        .pulse-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 6px;
        }
        .pulse-active {
            background-color: #10b981;
            box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.25);
        }
        .pulse-inactive {
            background-color: #f43f5e;
            box-shadow: 0 0 0 2px rgba(244, 63, 94, 0.25);
        }

        /* Section Cards */
        .ufw-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            overflow: hidden;
            margin-bottom: 12px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        }
        .ufw-card-header {
            padding: 8px 12px;
            background: #f8fafc;
            border-bottom: 1px solid #e2e8f0;
            font-size: 12px;
            font-weight: 700;
            color: #0f172a;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .ufw-card-body {
            padding: 12px;
        }

        /* Tables */
        .table-ufw {
            width: 100%;
            margin-bottom: 0;
            border-collapse: collapse;
            font-size: 12px;
        }
        .table-ufw th {
            background: #f8fafc !important;
            color: #64748b !important;
            font-size: 10px !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
            padding: 7px 10px !important;
            border: 1px solid #e2e8f0 !important;
        }
        .table-ufw td {
            padding: 8px 10px !important;
            vertical-align: middle !important;
            border: 1px solid #f1f5f9 !important;
            color: #334155 !important;
        }
        .table-ufw tr:hover {
            background-color: #f8fafc !important;
        }

        /* Modern Form Elements */
        .ufw-input, input[type=text].ufw-input, input[type=number].ufw-input, select.ufw-input, textarea.ufw-input {
            width: 100% !important;
            max-width: 380px !important;
            padding: 5px 9px !important;
            font-size: 12px !important;
            font-family: var(--font-mono) !important;
            color: #1e293b !important;
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 4px !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
            outline: none !important;
            transition: all 0.15s ease !important;
            margin: 0 !important;
        }
        .ufw-input:focus, input[type=text].ufw-input:focus, select.ufw-input:focus, textarea.ufw-input:focus {
            border-color: var(--brand-primary) !important;
            box-shadow: 0 0 0 2px rgba(5, 150, 105, 0.15) !important;
        }
        .ufw-input-inline {
            display: inline-block !important;
            width: auto !important;
        }

        /* Modern Buttons */
        .btn-modern {
            display: inline-flex !important;
            align-items: center !important;
            gap: 4px !important;
            padding: 5px 11px !important;
            font-size: 11px !important;
            font-weight: 600 !important;
            border-radius: 4px !important;
            border: 1px solid transparent !important;
            cursor: pointer !important;
            transition: all 0.15s ease !important;
            text-decoration: none !important;
            white-space: nowrap !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
        }
        .btn-brand {
            background-color: var(--brand-primary) !important;
            color: #ffffff !important;
            border-color: var(--brand-primary) !important;
        }
        .btn-brand:hover {
            background-color: var(--brand-hover) !important;
            color: #ffffff !important;
        }
        .btn-danger-modern {
            background-color: #e11d48 !important;
            color: #ffffff !important;
            border-color: #e11d48 !important;
        }
        .btn-danger-modern:hover {
            background-color: #be123c !important;
            color: #ffffff !important;
        }
        .btn-warning-modern {
            background-color: #d97706 !important;
            color: #ffffff !important;
            border-color: #d97706 !important;
        }
        .btn-warning-modern:hover {
            background-color: #b45309 !important;
            color: #ffffff !important;
        }
        .btn-info-modern {
            background-color: #0284c7 !important;
            color: #ffffff !important;
            border-color: #0284c7 !important;
        }
        .btn-info-modern:hover {
            background-color: #0369a1 !important;
            color: #ffffff !important;
        }
        .btn-secondary-modern {
            background-color: #ffffff !important;
            color: #334155 !important;
            border-color: #cbd5e1 !important;
        }
        .btn-secondary-modern:hover {
            background-color: #f1f5f9 !important;
            color: #0f172a !important;
        }

        /* Quick Fill Chips */
        .port-quick-fill {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 4px;
            margin-top: 6px;
        }
        .port-chip {
            padding: 2px 7px !important;
            font-size: 10px !important;
            font-family: var(--font-mono) !important;
            font-weight: 600 !important;
            background: #f1f5f9 !important;
            color: #475569 !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 3px !important;
            cursor: pointer !important;
            transition: all 0.1s ease !important;
        }
        .port-chip:hover {
            background: #e2e8f0 !important;
            color: #0f172a !important;
            border-color: #cbd5e1 !important;
        }

        /* Terminal Console */
        .terminal-box {
            background-color: #0f172a;
            color: #e2e8f0;
            border: 1px solid #1e293b;
            border-radius: 6px;
            padding: 12px;
            font-family: var(--font-mono);
            font-size: 11px;
            line-height: 1.6;
            overflow-x: auto;
            white-space: pre-wrap;
        }

        /* Radio Pill Badges */
        .radio-pill-group label {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 12px;
            font-weight: 500;
            color: #334155;
            cursor: pointer;
            margin-right: 12px;
        }
    </style>
</head>
<body>
<div class="container-fluid">
END_HTML

    if ($result_msg) {
        print <<"RESULT_HTML";
<div class="status-banner status-active" style="margin-bottom: 12px;">
    <span>$result_msg</span>
</div>
RESULT_HTML
    }
}
1;
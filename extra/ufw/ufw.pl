#!/usr/bin/perl
use strict;
use File::Find;
use Fcntl qw(:DEFAULT :flock);
use Sys::Hostname qw(hostname);
use warnings;
use CGI qw(:standard);
use CGI::Carp qw(fatalsToBrowser);
use File::Glob 'bsd_glob';




our ($script, $images,$layout_file, %FORM, %in);
our $action;
our $default_path;

our $result_msg;
our $bootstrapcss;
our $jqueryjs;
our $bootstrapjs;
my $LIB_PATH = '/usr/local/ufw';

use lib '/usr/local/ufw';
require 'header.pl';
require 'footer.pl';
require 'logs.pl';
require 'main.pl';
require 'msg.pl';
my $q = CGI->new;

# Get POST params



$script = "/whm/iframe/";
$images = "/media/csf";
 $bootstrapcss = "<link rel='stylesheet' href='$images/bootstrap/css/bootstrap.min.css'>";
 $jqueryjs = "<script src='$images/jquery.min.js'></script>";
 $bootstrapjs = "<script src='$images/bootstrap/js/bootstrap.min.js'></script>";

# Result message for user feedback

my $file = $ARGV[0];
unless (-e $file) {die "Cannot find tempfile [$file]"}


open (my $DATA, "<", $file);
my $buffer = <$DATA>;
close ($DATA);
my @pairs = split(/&/, $buffer);
foreach my $pair (@pairs) {
	my ($name, $value) = split(/=/, $pair);
	$value =~ tr/+/ /;
	$value =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack("C", hex($1))/eg;
	$FORM{$name} = $value;
}

$action = $FORM{action};
my $ip = $FORM{ip} || '';
my $port = $FORM{port} || '';
my $protocol = $FORM{protocol} || 'tcp';
my $comment = $FORM{comment} || '';
my $rule_number = $FORM{rule_number} || '';
my $search_term = $FORM{search_term} || '';

use strict;
use warnings;
use File::Glob 'bsd_glob';


# Helper sub to escape HTML special chars (for safety)
sub html_escape {
    my $text = shift;
    return '' unless defined $text;
    $text =~ s/&/&amp;/g;
    $text =~ s/</&lt;/g;
    $text =~ s/>/&gt;/g;
    $text =~ s/"/&quot;/g;
    $text =~ s/'/&#39;/g;
    return $text;
}

sub conf_list_head {
    my $folder  = "/usr/local/ufw/config";
    my $pattern = "*.conf";

    my @conf_files = bsd_glob("$folder/$pattern");

    # Extract config names uppercase
    my @conf_names = map { my ($n) = m{([^/]+)\.conf$}; uc($n) } @conf_files;

    # Define desired order priority for some known names
    my %priority = (
        SSH      => 1,
        FTP      => 2,
        MAIL     => 3,
        OLSPANEL => 4,
    );

    # Sort with priority, then alphabetically for others
    my @sorted_names = sort {
        ( ($priority{$a} // 999) <=> ($priority{$b} // 999) )
        ||
        ( $a cmp $b )
    } @conf_names;

    # Map sorted names back to full path
    my %name_to_file = map {
        my ($n) = m{([^/]+)\.conf$};
        (uc($n) => $_)
    } @conf_files;

    print qq{
<ul class="nav nav-tabs" id="myTabsd" style="margin-bottom: 12px; border-bottom: 1px solid #e2e8f0;">
};

    foreach my $name (@sorted_names) {
        # To set only the first <li> active, use index
        my $active_class = ($name eq $sorted_names[0]) ? ' class="active"' : '';
        print qq{
<li$active_class><a data-toggle="tab" href="#id_$name">$name</a></li>
};
    }

    print qq{
</ul>
};
}

sub conf_list {
    my $folder  = "/usr/local/ufw/config";
    my $pattern = "*.conf";

    my @conf_files = bsd_glob("$folder/$pattern");

    # Extract config names uppercase
    my @conf_names = map { my ($n) = m{([^/]+)\.conf$}; uc($n) } @conf_files;

    # Define desired order priority for some known names
    my %priority = (
        SSH      => 1,
        FTP      => 2,
        MAIL     => 3,
        OLSPANEL => 4,
    );

    # Sort with priority, then alphabetically for others
    my @sorted_names = sort {
        ( ($priority{$a} // 999) <=> ($priority{$b} // 999) )
        ||
        ( $a cmp $b )
    } @conf_names;

    # Map sorted names back to full path
    my %name_to_file = map {
        my ($n) = m{([^/]+)\.conf$};
        (uc($n) => $_)
    } @conf_files;

    my $first = 1;
    foreach my $name (@sorted_names) {
        my $conf_file = $name_to_file{$name};
        my $config = parse_conf_file($conf_file);
        my $active_class = $first ? " active" : "";
        $first = 0;
        print qq{
<div id="id_$name" class="tab-pane$active_class">	  
<form action="" method="post" id="ufw_status_form_$name" class="ufw-form" style="margin: 0;">
<div class="ufw-card">
<div class="ufw-card-header">
    <span><i class="mdi mdi-shield-account text-brand"></i> [$name] Security &amp; Intrusion Triggers</span>
    <span style="font-size: 10px; color: #94a3b8; font-weight: normal;">Threshold Configurations</span>
</div>
<table class="table-ufw">
<tbody>

<tr>
<td style="width:240px; font-weight: 600;">Protection Daemon Status</td>
<td>
  <input type="hidden" name="action" value="set_status">
  <input type="hidden" name="config_name" value="$name">
  <div class="radio-pill-group">
    <label><input type="radio" name="STATUS" value="1" @{[($config->{STATUS} // '') eq '1' ? 'checked' : '']}> <strong style="color: #059669;">Active</strong></label>
    <label style="margin-left: 14px;"><input type="radio" name="STATUS" value="0" @{[($config->{STATUS} // '') eq '0' ? 'checked' : '']}> <span style="color: #64748b;">Inactive</span></label>
  </div>
</td>
</tr>
};

        if (!exists $priority{$name}) {
            print qq{
<tr>
<td style="font-weight: 600;">Log Files</td>
<td>
  <input type="text" name="LOG_FILE" class="ufw-input" value="@{[ html_escape($config->{LOG_FILE} // '') ]}" required>
  <br><small style="color: #94a3b8;">Use comma (,) for multiple log file paths</small>
</td>
</tr>
};
        }

        print qq{
<tr>
<td style="font-weight: 600;">Temporary Block Duration (min)</td>
<td>
  <input type="number" name="TEMP_BLOCK_DURATION" class="ufw-input ufw-input-inline" style="width: 120px !important;" value="@{[ html_escape($config->{TEMP_BLOCK_DURATION} // '') ]}" min="1" required>
  <br><small style="color: #94a3b8;">Duration in minutes to isolate IP</small>
</td>
</tr>

<tr>
<td style="font-weight: 600;">Failed Attempts Threshold</td>
<td>
  <input type="number" name="TEMP_BLOCK_THRESHOLD" class="ufw-input ufw-input-inline" style="width: 120px !important;" value="@{[ html_escape($config->{TEMP_BLOCK_THRESHOLD} // '') ]}" min="1" required>
  <br><small style="color: #94a3b8;">Maximum failed logins before triggering temporary block</small>
</td>
</tr>

<tr>
<td style="font-weight: 600;">Failed Attempts Window (min)</td>
<td>
  <input type="number" name="TEMP_WINDOW" class="ufw-input ufw-input-inline" style="width: 120px !important;" value="@{[ html_escape($config->{TEMP_WINDOW} // '') ]}" min="1" required>
  <br><small style="color: #94a3b8;">Time window in minutes to accumulate failed attempts</small>
</td>
</tr>

<tr>
<td style="font-weight: 600;">Permanent Block Threshold (Temp count)</td>
<td>
  <input type="number" name="PERM_BLOCK_THRESHOLD" class="ufw-input ufw-input-inline" style="width: 120px !important;" value="@{[ html_escape($config->{PERM_BLOCK_THRESHOLD} // '') ]}" min="1" required>
  <br><small style="color: #94a3b8;">Number of temporary blocks before permanently blacklisting</small>
</td>
</tr>

<tr>
<td style="font-weight: 600;">Permanent Block Window (hrs)</td>
<td>
  <input type="number" name="PERM_WINDOW" class="ufw-input ufw-input-inline" style="width: 120px !important;" value="@{[ html_escape($config->{PERM_WINDOW} // '') ]}" min="1" required>
  <br><small style="color: #94a3b8;">Window in hours to evaluate repeat temp block offences</small>
</td>
</tr>
};

        if (!exists $priority{$name}) {
            print qq{
<tr>
<td style="font-weight: 600;">Keywords</td>
<td>
  <textarea name="KEYWORD" class="ufw-input" style="height: 60px;" required>@{[ html_escape($config->{KEYWORD} // '') ]}</textarea>
  <br><small style="color: #94a3b8;">Comma-separated keywords matching failed log events</small>
</td>
</tr>
};
        }

        print qq{
<tr>
<td style="font-weight: 600;">Ignore / Whitelist IPs</td>
<td>
  <textarea name="IGNORE_IP" class="ufw-input" style="height: 60px;">@{[ html_escape($config->{IGNORE_IP} // '') ]}</textarea>
  <br><small style="color: #94a3b8;">Comma-separated trusted IPs that should never be banned</small>
</td>
</tr>

<tr>
<td colspan="2" style="background: #f8fafc; padding: 10px 14px;">
  <button type="submit" class="btn-modern btn-brand">
    <i class="mdi mdi-content-save-outline"></i> Save $name Configuration
  </button>
</td>
</tr>

</tbody>
</table>
</div>
</form>
</div>
};
    }
}


sub save_conf_file {
    my ($file_path, $new_values) = @_;

    # Read existing lines
    open my $in, '<', $file_path or return ("Failed to open $file_path for reading: $!", 1);
    my @lines = <$in>;
    close $in;

    my %seen_keys;
    my @out_lines;

    foreach my $line (@lines) {
        if ($line =~ /^(\s*#?\s*)([A-Z_]+)\s*=\s*(.*)$/) {
            my ($prefix, $key) = ($1, $2);
            if (exists $new_values->{$key}) {
                $line = "${prefix}${key} = $new_values->{$key}\n";
                $seen_keys{$key} = 1;
            }
        }
        push @out_lines, $line;
    }

    # Add keys that were not present
    foreach my $key (keys %$new_values) {
        next if $seen_keys{$key};
        push @out_lines, "$key = $new_values->{$key}\n";
    }

    # Write lines back
    open my $out, '>', $file_path or return ("Failed to open $file_path for writing: $!", 1);
    print $out @out_lines;
    close $out;

    return ("Configuration saved successfully to $file_path", 0);
}



# -------------------------------------------------
# Function 2: Parse a .conf file into a hash
# -------------------------------------------------
sub parse_conf_file {
    my ($file) = @_;
    my %config;

    open my $fh, '<', $file or do {
        warn "Could not open $file: $!";
        return {};
    };

    while (my $line = <$fh>) {
        chomp $line;
        $line =~ s/^\s+|\s+$//g;     # Trim spaces
        next if $line =~ /^#/;       # Skip comments
        next if $line eq '';         # Skip empty lines

        if ($line =~ /^([A-Za-z0-9_]+)\s*=\s*(.*)$/) {
            my ($key, $value) = ($1, $2);
            $value =~ s/^\s+|\s+$//g; # Trim spaces
            $config{$key} = $value;
        }
    }

    close $fh;
    return \%config;
}


sub read_file {
    my ($path) = @_;
    open my $fh, '<', $path or die "Can't open $path: $!";
    local $/;
    my $content = <$fh>;
    close $fh;
    return $content;
}

sub execute_ufw_command {
    my ($command) = @_;
    my $full_command = "sudo ufw $command 2>&1";
    my $output = `$full_command`;
    my $exit_code = $? >> 8;
    return ($output, $exit_code);
}

sub get_ufw_status {
    my ($output, $exit_code) = execute_ufw_command("status verbose");

    if ($exit_code == 0) {
        # Look for line like "Status: active"
        if ($output =~ /^Status:\s*(\w+)/mi) {
            my $status = lc($1);  # Get "active" or "inactive"
            return $status;
        } else {
            return "unknown";  # If not found
        }
    } else {
        return "error";  # Command failed
    }
}

sub print_rules_table {
    my $rules_text = get_ufw_rules();
    my @lines = split /\n/, $rules_text;
    my $html = '';

    $html .= qq{
        <script>
        function deleteRule(form, ruleNum) {
            if (!confirm('Are you sure you want to delete rule number [' + ruleNum + ']?')) return false;

            var xhr = new XMLHttpRequest();
            xhr.open('POST', "/whm/iframe/");
            xhr.onload = function() {
                if (xhr.status === 200) {
                    var row = form.closest('tr');
                    if (row) row.parentNode.removeChild(row);
                } else {
                    alert('Failed to delete rule: ' + xhr.statusText);
                }
            };
            xhr.onerror = function() {
                alert('Request error');
            };

            var formData = new FormData(form);
            xhr.send(formData);

            return false;
        }
        </script>

        <div class="ufw-card" style="margin-top: 6px;">
            <div class="ufw-card-header">
                <span><i class="mdi mdi-table text-brand"></i> Configured UFW Rules</span>
                <button class="btn-modern btn-secondary-modern" onclick="window.history.back();" style="padding: 2px 8px; font-size: 11px;">
                    <i class="mdi mdi-arrow-left"></i> Return
                </button>
            </div>
            <div style="overflow-x: auto;">
            <table class="table-ufw">
                <thead>
                    <tr>
                        <th style="width: 45px; text-align: center;">#</th>
                        <th>Target / Port</th>
                        <th>Action</th>
                        <th>Direction</th>
                        <th>Source / IP</th>
                        <th>Note / Comment</th>
                        <th>Options</th>
                        <th style="text-align: right; width: 80px;">Action</th>
                    </tr>
                </thead>
                <tbody>
    };

    foreach my $line (@lines) {
        if ($line =~ /^\[\s*(\d+)\]\s+(.*)$/) {
            my $num = $1;
            my $raw = $2;

            my $note = "";
            if ($raw =~ /^(.*?)(?:\s+#\s*(.*))?$/) {
                $raw = $1;
                $note = defined $2 ? $2 : "";
            }

            my ($place, $action, $direction, $ip) = ("", "", "IN", "");
            if ($raw =~ /^(.*?)\s+(ALLOW|DENY|REJECT|LIMIT)\s+(IN|OUT|FWD)?\s*(.*)$/i) {
                $place     = $1;
                $action    = uc($2);
                $direction = defined $3 ? uc($3) : "IN";
                $ip        = defined $4 ? $4 : "";
            } else {
                my @parts = split /\s+/, $raw;
                $place     = shift @parts // "";
                $action    = shift @parts // "";
                $direction = shift @parts // "";
                $ip        = join(" ", @parts);
            }

            my $action_badge = ($action =~ /ALLOW/i) 
                ? qq{<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 uppercase" style="display:inline-block; padding: 2px 6px; border-radius: 3px; font-weight: bold; background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0;">$action</span>}
                : qq{<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200 uppercase" style="display:inline-block; padding: 2px 6px; border-radius: 3px; font-weight: bold; background: #fff1f2; color: #be123c; border: 1px solid #fecdd3;">$action</span>};

            $html .= qq{
                <tr>
                    <td style="text-align: center; font-family: var(--font-mono); font-weight: 700; color: #64748b;">[$num]</td>
                    <td style="font-family: var(--font-mono); font-weight: 600; color: #0f172a;">$place</td>
                    <td>$action_badge</td>
                    <td style="font-family: var(--font-mono); font-weight: 600; color: #475569;">$direction</td>
                    <td style="font-family: var(--font-mono); color: #334155;">$ip</td>
                    <td style="color: #64748b; font-size: 11px;">$note</td>
                    <td style="text-align: right;">
                        <form action="" method="post" class="ufw-form" onsubmit="return deleteRule(this, $num);" style="margin:0;">
                            <input type="hidden" name="action" value="ufw_remove_rule">
                            <input type="hidden" name="rule_number" value="$num">
                            <button type="submit" class="btn-modern btn-danger-modern" style="padding: 2px 7px; font-size: 10px;">
                                <i class="mdi mdi-delete-outline"></i> Delete
                            </button>
                        </form>
                    </td>
                </tr>
            };
        }
    }

    $html .= qq{
                </tbody>
            </table>
            </div>
            <div style="padding: 8px 12px; background: #f8fafc; border-top: 1px solid #e2e8f0; display: flex; justify-content: flex-end;">
                <button class="btn-modern btn-secondary-modern" onclick="window.history.back();">
                    <i class="mdi mdi-arrow-left"></i> Return to Firewall Console
                </button>
            </div>
        </div>
    };

    return $html;
}



sub get_ufw_rules {
    my ($output, $exit_code) = execute_ufw_command("status numbered");
    if ($exit_code == 0) {
        return $output;
    } else {
        return "Error getting UFW rules: $output";
    }
}

sub add_ufw_ip_rule {
    my ($ip, $action, $comment) = @_;
	
    my $command = "$action from $ip";
    if ($comment) {
        $command .= " comment '$comment'";
    }
    my ($output, $exit_code) = execute_ufw_command($command);
	restart_ufw();
    return ($output, $exit_code);
}

sub add_ufw_port_rule {
    my ($port, $protocol, $action) = @_;
    my $command = "$action $port/$protocol";
    my ($output, $exit_code) = execute_ufw_command($command);
	restart_ufw();
    return ($output, $exit_code);
}

sub remove_ufw_rule {
    my ($rule_number) = @_;
    my $command = "delete $rule_number";
    my ($output, $exit_code) = execute_ufw_command("--force $command");
	restart_ufw();
    return ($output, $exit_code);
}

sub search_ufw_rules {
    my ($search_term) = @_;
    my $rules = get_ufw_rules();
    my @matching_rules = ();
    
    foreach my $line (split /\n/, $rules) {
        if ($line =~ /\Q$search_term\E/i) {
            push @matching_rules, $line;
        }
    }
    
    return join("\n", @matching_rules);
}

sub enable_ufw {
    my ($output, $exit_code) = execute_ufw_command("--force enable");
    return ($output, $exit_code);
}

sub disable_ufw {
    my ($output, $exit_code) = execute_ufw_command("--force disable");
    return ($output, $exit_code);
}

sub reset_ufw {
    my ($output, $exit_code) = execute_ufw_command("--force reset");
    return ($output, $exit_code);
}

sub restart_ufw {
    my ($output, $exit_code) = execute_ufw_command("reload");
    return ($output, $exit_code);
}


# Define this once at the top of your script
# Assume you already have a sub to generate options, example:
sub generate_log_options {
    my $log_file_list_path = "$LIB_PATH/log_files.txt";
    my @log_paths;

    open my $fh, '<', $log_file_list_path or die "Cannot open log list: $!";
    while (<$fh>) {
        chomp;
        s/,\s*$//; # remove trailing commas/spaces
        push @log_paths, $_ if $_;
    }
    close $fh;

    my $html = "";
    for my $i (0..$#log_paths) {
        my $path = $log_paths[$i];
        my $size_kb = "0 kb";
        if (-e $path) {
            my $size_bytes = -s $path;
            $size_kb = int($size_bytes / 1024);
        }
        $html .= qq{<option value="$i">$path ($size_kb kb)</option>\n};
    }
    return $html;
}




sub logtailcmd {
    my $query = CGI->new;

    # Get params from URL or form
    my $lognum = $FORM{lognum} // 0;
    my $lines  = $FORM{lines}  // 100;

    # Sanitize
    $lognum =~ s/\D//g;
    $lines  =~ s/\D//g;

    # Path to log_file.txt
    my $log_file = "$LIB_PATH/log_files.txt";

    # Read all log paths
    my @log_paths;
    if (open my $fh, '<', $log_file) {
        while (<$fh>) {
            chomp;
            s/,\s*$//;         # Remove trailing comma/space
            push @log_paths, $_ if $_;
        }
        close $fh;
    } else {
        return 0;
    }

    # Get the selected log file by index
    my $logfile = $log_paths[$lognum];
    unless ($logfile && -e $logfile) {
        return "<---- ".$logfile." is currently empty ---->";
    }

    # Tail output
    my $output = `tail -n $lines '$logfile' 2>&1`;

    return $output;
}



sub get_content_html {
    my %action_to_layout = (
        'main'    => '/usr/local/ufw/main.html',
       
    );
    my $layout_path = $action_to_layout{$action} // '/usr/local/ufw/main.html';
    my $content_html = read_file($layout_path);

    print_header($result_msg, $bootstrapcss, $jqueryjs, $bootstrapjs, $images);
   print $content_html;
    print_footer();
}



# Process UFW actions
if ($action) {
    if ($action eq 'ufw_enable') {
        my ($output, $exit_code) = enable_ufw();
        $result_msg = $output;
    }
    elsif ($action eq 'ufw_disable') {
        my ($output, $exit_code) = disable_ufw();
         $result_msg = $output;
    }
    elsif ($action eq 'ufw_restart') {
        my ($output, $exit_code) = restart_ufw();
         $result_msg = $output;
    }
    elsif ($action eq 'ufw_allow_ip' && $ip) {
        my ($output, $exit_code) = add_ufw_ip_rule($ip, 'allow', $comment);
		
         $result_msg = $output;
    }
    elsif ($action eq 'ufw_deny_ip' && $ip) {
        my ($output, $exit_code) = add_ufw_ip_rule($ip, 'insert 1 deny', $comment);
		
         $result_msg = $output;
    }
    elsif ($action eq 'ufw_allow_port' && $port) {
        my ($output, $exit_code) = add_ufw_port_rule($port, $protocol, 'allow');
		
         $result_msg = $output;
    }
    elsif ($action eq 'ufw_deny_port' && $port) {
        my ($output, $exit_code) = add_ufw_port_rule($port, $protocol, 'deny');
		
         $result_msg = $output;
    }
    elsif ($action eq 'ufw_remove_rule' && $rule_number) {
        my ($output, $exit_code) = remove_ufw_rule($rule_number);
		
         $result_msg = $output;
    }
	elsif ($action eq 'set_status') {
    my $conf_name = lc($FORM{config_name} // '');  # lowercase, or empty if not set
    my $file = "/usr/local/ufw/config/$conf_name.conf";

    my $new_vals = {
        STATUS               => $FORM{STATUS} // '0',
        TEMP_BLOCK_DURATION  => $FORM{TEMP_BLOCK_DURATION} // '',
        TEMP_BLOCK_THRESHOLD => $FORM{TEMP_BLOCK_THRESHOLD} // '',
        TEMP_WINDOW          => $FORM{TEMP_WINDOW} // '',
        PERM_BLOCK_THRESHOLD => $FORM{PERM_BLOCK_THRESHOLD} // '',
        PERM_WINDOW          => $FORM{PERM_WINDOW} // '',
        IGNORE_IP            => $FORM{IGNORE_IP} // '',
    };

    # Only add if defined and non-empty
    $new_vals->{KEYWORD}  = $FORM{KEYWORD} if defined $FORM{KEYWORD} && length $FORM{KEYWORD};
    $new_vals->{LOG_FILE} = $FORM{LOG_FILE} if defined $FORM{LOG_FILE} && length $FORM{LOG_FILE};

    my ($output, $exit_code) = save_conf_file($file, $new_vals);
    $result_msg = $output;
}

    elsif ($action eq 'ufw_search' && $search_term) {
        my $search_results = search_ufw_rules($search_term);
		if ($search_results) {
         $result_msg = $search_results;
		}else{
		$result_msg = "Search not match";	
		}
    }
    
    
}
if ($result_msg) {
 print_header($result_msg, $bootstrapcss, $jqueryjs, $bootstrapjs, $images);   
    print_msg($result_msg);
    print_footer();
}
my $main_h='main';
my $content_file = '';
my $content_html ="";


if ($action eq 'logtail') {
   my $options_html = generate_log_options();
    print_header($result_msg, $bootstrapcss, $jqueryjs, $bootstrapjs, $images);
   
   print_logs($options_html);
    print_footer();
}
elsif ($action eq 'logtailcmd') {
    $content_html = logtailcmd();
	print $content_html;
}elsif ($action eq 'ufw_list_rules') {
       
    print_header($result_msg, $bootstrapcss, $jqueryjs, $bootstrapjs, $images);   
    print_msg(get_ufw_rules());
    print_footer();
}elsif ($action eq 'ufw_list_rules_table') {
       
    print_header($result_msg, $bootstrapcss, $jqueryjs, $bootstrapjs, $images);   
    print print_rules_table();
    print_footer();
    }
	
else {
    print_header($result_msg, $bootstrapcss, $jqueryjs, $bootstrapjs, $images);
   
   print_main();
    print_footer();
}



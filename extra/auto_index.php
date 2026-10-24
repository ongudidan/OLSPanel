<?php
// Get username from HTTP header, query string, or fallback to root
$username = $_SERVER['PANEL_USERNAME'] ?? $_GET['username'] ?? '';
if (empty($username) || $username === 'admin') {
    $username = 'root';
}

function get_imunify_token($user) {
    $escaped = escapeshellarg($user);
    $output = trim((string)shell_exec("sudo /usr/bin/imunify-antivirus login get --username $escaped 2>/dev/null"));
    if (empty($output)) {
        $output = trim((string)shell_exec("/usr/bin/imunify-antivirus login get --username $escaped 2>/dev/null"));
    }
    if (!empty($output) && strpos($output, ' ') === false && strpos($output, "\n") === false && strlen($output) > 20) {
        return $output;
    }
    return '';
}

$token = get_imunify_token($username);
if (empty($token) && $username !== 'root') {
    $token = get_imunify_token('root');
}

if (!empty($token)) {
    header("Location: /3rdparty/imunifyfav/#/login?token=" . urlencode($token));
} else {
    header("Location: /3rdparty/imunifyfav/");
}
exit;

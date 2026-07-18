<?php

declare(strict_types=1);

$cfg['blowfish_secret'] = 'fgkj456hfrrhbgcdqbvdgmnnnbvbf457gggh'; /* YOU MUST FILL IN THIS FOR COOKIE AUTH! */

$i = 0;

$i++;

$cfg['Servers'][$i]['AllowNoPassword'] = false;
$cfg['Servers'][$i]['auth_type'] = 'signon';
$cfg['Servers'][$i]['SignonSession'] = 'SignonSession';
$cfg['Servers'][$i]['SignonURL'] = 'auto_login.php';
$cfg['Servers'][$i]['LogoutURL'] = "auto_login.php?logout=$_SESSION[PMA_PORT]";
$cfg['Servers'][$i]['hide_db'] = 'panel';

$cfg['UploadDir'] = '';
$cfg['SaveDir'] = '';

$pma_user = function_exists('posix_getpwuid') ? posix_getpwuid(posix_geteuid())['name'] : 'default';
$pma_temp_dir = '/tmp/pma_temp_' . $pma_user;
if (!is_dir($pma_temp_dir)) {
    @mkdir($pma_temp_dir, 0700, true);
}
$cfg['TempDir'] = $pma_temp_dir;

// Restrict database view to a single database if specified in session
if (isset($_SESSION['PMA_single_signon_only_db']) && !empty($_SESSION['PMA_single_signon_only_db'])) {
    $cfg['Servers'][$i]['only_db'] = $_SESSION['PMA_single_signon_only_db'];
}

// Disallow database creation and dropping globally within phpMyAdmin
$cfg['ShowCreateDb'] = false;
$cfg['AllowUserDropDatabase'] = false;

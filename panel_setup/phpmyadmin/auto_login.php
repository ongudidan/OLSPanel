<?php
function decode_base64_to_json($base64_data) {
    // Decode the Base64 string
    $json_data = base64_decode($base64_data);

    // Convert the JSON string back to an array
    $data = json_decode($json_data, true);

    if ($data === null) {
        die("Invalid JSON data.");
    }

    return $data;
}

// Example usage

define("PMA_SIGNON_INDEX", 1);

try{

define('PMA_SIGNON_SESSIONNAME', 'SignonSession');
define('PMA_DISABLE_SSL_PEER_VALIDATION', TRUE);

 if(isset($_GET['logout'])){
	$port= isset($_SESSION['PMA_PORT']) ? $_SESSION['PMA_PORT'] : '/';
   $params = session_get_cookie_params();
   setcookie(session_name(), '', time() - 86400, $params["path"], $params["domain"], $params["secure"], $params["httponly"] );
   session_destroy();
   // Redirect back to the panel port (stored in PMA_PORT session)
   header("Location: " . $port);
   return;
}
else if(isset($_GET['password'])){

    session_name(PMA_SIGNON_SESSIONNAME);
    @session_start();
	

$decrypted_data = decode_base64_to_json($_GET['password']);
$username = $decrypted_data['user'];
$password = $decrypted_data['pass'];
$port = $decrypted_data['port'];
$_SESSION['PMA_PORT'] = $port;

$db = isset($decrypted_data['db']) ? $decrypted_data['db'] : '';
$_SESSION['PMA_single_signon_only_db'] = $db;

    $_SESSION['PMA_single_signon_user'] = $username;
    $_SESSION['PMA_single_signon_password'] = $password;
    $_SESSION['PMA_single_signon_host'] = 'localhost';


    @session_write_close();

    // Redirect to phpMyAdmin using the same origin (scheme + host + port) that the
    // panel is running on. Using $port (e.g. https://1.2.3.4:4263) ensures the
    // browser sends the SignonSession cookie on the correct origin.
    header('Location: ' . rtrim($port, '/') . '/phpmyadmin/index.php?server=' . PMA_SIGNON_INDEX);
}
}catch (Exception $e) {
    echo 'Caught exception: ',  $e->getMessage(), "\n";
    $params = session_get_cookie_params();
    setcookie(session_name(), '', time() - 86400, $params["path"], $params["domain"], $params["secure"], $params["httponly"] );
    session_destroy();
    header('Location: /');
    return;
}


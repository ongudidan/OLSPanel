<?php

// INDEX Files need to be defined as per the Control Panel
$globals['index'] = 'index.php?';
$globals['admin_index'] = 'index.php?';

$globals['softpanel'] = 'olspanel';

class softpanel{

	var $loaded = 0;
	var $unique;
	var $rawdata = array();
	var $user;
	var $spaceremain;
	var $domainroots;
	var $mysql = array();
	var $theme = array();
	var $env;
	
	function __construct(){
	
		global $cpanel;
		$path = __DIR__;
$pos = strpos($path, 'mypanel');

if ($pos !== false) {
    $base_path = substr($path, 0, $pos + strlen('mypanel'));
}

require_once $base_path . "/user.php";

		
		$currentPath = $_SERVER['REQUEST_URI']; // The part of the URL after the domain

// Check if the path contains 'softaculous/index.php'
// Normalize the URL path by removing redundant slashes
$currentPath = preg_replace('#/+#', '/', $_SERVER['REQUEST_URI']);

if (strpos($currentPath, 'softaculous/index.php') !== false) {
    // Redirect to the root
    //header("Location: /softaculous/enduser/index.php");
   // exit;
}



 if (!empty($_GET['ols_session'])) {
        $decrypted_data = $this->decode_base64_to_json($_GET['ols_session']);

        $this->api_key = $decrypted_data['api'];
        $this->username = $decrypted_data['user'];
$this->olspanel = new olspanel($this->username);
        $parms = ['v' => 1];
        $results = $this->olspanel->loadUser();
        if (!empty($results['id'])) {
            // Set cookies that expire in 1 day (adjust as needed)
            setcookie("userid", $results['id'], time() + 86400, "/");
            setcookie("full_name", $results['full_name'], time() + 86400, "/");
            setcookie("email", $results['email'], time() + 86400, "/");
            setcookie("api", $decrypted_data['api'], time() + 86400, "/");
            setcookie("username", $decrypted_data['user'], time() + 86400, "/");

            // Store them in $_COOKIE right away for current request
            $_COOKIE['userid'] = $results['id'];
            $_COOKIE['full_name'] = $results['full_name'];
            $_COOKIE['email'] = $results['email'];
            $_COOKIE['api'] = $decrypted_data['api'];
            $_COOKIE['username'] = $decrypted_data['user'];
        }
    }

  if (php_sapi_name() != 'cli') {
    if (empty($_COOKIE['userid'])) {
        header("Location: /");
        exit;
    }
}

    // Assign values from cookies
    $this->userid = $_COOKIE['userid'];
    $this->username = $_COOKIE['username'];
    $this->full_name = $_COOKIE['full_name'];
    $this->email = $_COOKIE['email'];
    $this->api_key = $_COOKIE['api'];

        // Read the password from the file (make sure the file is readable only by the panel)
        
		$this->theme['softimages'] = 'softimages';// Relative to the accessed URL
		$this->theme['url'] = 'themes';// Relative to the accessed URL
		$this->theme['admin_url'] = 'enduser/themes';// Relative to the accessed URL
		$this->theme['logout'] = '/logout/'; // Relative to the accessed URL
		$this->theme['panel_url'] = '/'; // Relative to the accessed URL
		
		// Are you a Dedicated or Virtual Server
		$this->env = '';
		
		if(defined('SOFTADMIN')) return true;

		//Load the Raw Data
		//$this->rawdata = $this->rawdata();
		
		//Load the Data
		//$this->user = $this->userdata();
		//$this->domainroots = $this->domainroots();
		//$this->spaceremain = $this->spaceremain();
		
		//In Cpanel we are using this since further calls need to be accessed again
		$this->loaded = 1;
	
	}
	
private function decode_base64_to_json($base64_data) {
    // Decode the Base64 string
    $json_data = base64_decode($base64_data);

    // Convert the JSON string back to an array
    $data = json_decode($json_data, true);

    if ($data === null) {
        die("Invalid JSON data.");
    }

    return $data;
}
	
private function auth_me($type, $parms) {
   
/*
   // Determine protocol and host
    $host = $_SERVER['HTTP_HOST']; // Gets current domain or IP
  
    // Construct full API URL
  $url = 'https://'. $host.'/api/' . $type;

    // Initialize cURL
    $curl = curl_init();

    // Set cURL options
    curl_setopt_array($curl, array(
        CURLOPT_URL => $url,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_ENCODING => '',
        CURLOPT_MAXREDIRS => 10,
        CURLOPT_TIMEOUT => 30,  // Set a timeout for better control
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
        CURLOPT_CUSTOMREQUEST => 'POST',
        
        // Send parameters as POST fields (use http_build_query for proper encoding)
        CURLOPT_POSTFIELDS => http_build_query($parms),

        // Send username and API key in headers
        CURLOPT_HTTPHEADER => array(
            'username: ' . $this->username,
            'apikey: ' . $this->api_key,
        ),

        // Disable SSL verification (for development only, ideally turn it on in production)
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => false,
    ));

    // Execute cURL and capture the response
   $response = curl_exec($curl);

   curl_close($curl);

   
    // Decode the JSON response
    $data = json_decode($response, true);

   

    return $data;  // Return the decoded JSON data
	*/
}

	
	
	// A unique string to identify the server
	function unique(){
		return '';
	}
	
	// If any raw data is required to be loaded first for the user info
	function rawdata(){
		//return $_CPANEL;
	}
	
	function userdata(){
		global $loaded_scripts, $globals;
	 $parms = ['v' => 1];
    $results = $this->olspanel->home(); // Assuming 'home' returns user limits
    
		$user = array();
		$user['name'] = $this->username; // Username of the account used for MySQL purposes
		$user['displayname'] = $this->username;// For displaying the actual name
		$user['email'] = $this->email; // Email of the account
		$user['domain'] = $results['main_domain']; // Primary Domain of the account
		$user['homedir'] = '/home/'.$this->username.'';// Home Dir of the account
		
		
		$user['softdir'] = '/home/'.$this->username.'';
		
		//To check whether the user belongs to any ACL plan and load iscripts according to plan (Version 3.4)
		if(file_exists($globals['path'].'/conf/plans.acl')){
			$get_user_plan = unserialize(implode('', file($globals['path'].'/conf/plans.acl')));
			if(!empty($get_user_plan['users'][$user['name']])){
				$temp = unserialize(implode('', file($globals['path'].'/conf/'.$get_user_plan['users'][$user['name']].'.plan')));
				$loaded_scripts = $temp['scripts'];
			}
		}
		
		return $user;
		
	}
	
	
function domainroots(){
    $parms = ['v' => 1];
    $results = $this->olspanel->domain_list();

    $array = array();

    // Check if API returned a valid list
    if (!empty($results) && is_array($results)) {
        foreach ($results as $item) {
            if (isset($item['domain']) && isset($item['path'])) {
                $array[$item['domain']] = $item['path']; // Use domain as key and path as value
            }
        }
    }

    return $array;
}
	


	//The Host of the Database
	function dbhost($type = 'mysql'){
		return 'localhost'; // If any other host please return that!	
	}
	
	//The Maximum Number of Database
	function maxdb($type = 'mysql') {
    $parms = ['v' => 1];
    $results = $this->olspanel->home(); // Assuming 'home' returns user limits
    
    // Ensure db_limit exists and is a valid integer-like value
    if (isset($results['db_limit']) && is_numeric($results['db_limit'])) {
        return (int)$results['db_limit'];
    } else {
        // Default value if not found or not valid
        return 100000;
    }
}


	
	//List the databases of this user
	function listdbs($type = 'mysql') {
    $parms = ['v' => 1];
    $results = $this->auth_me("database_list/", $parms); 

    $array = array();

    // Make sure the response contains 'databases' and is an array
    if (!empty($results['databases']) && is_array($results['databases'])) {
        foreach ($results['databases'] as $dbname) {
            $array[$dbname] = $dbname; // Add each db name as key and value
        }
    }

    return $array;
}

	
	//List the MySQL database users
	function listdbusers($type = 'mysql') {
    // Make the authenticated API request to get the list of DB users
    $parms = ['v' => 1];
    $results = $this->auth_me("database_userlist/", $parms);

    $array = array();

    if (!empty($results['users']) && is_array($results['users'])) {
        foreach ($results['users'] as $user) {
            $array[$user] = $user; // Use the username as both key and value
        }
    }

    return $array;
}


	
	function dbsused() {
    $parms = ['v' => 1];
    $results =  $this->olspanel->home();
    return (int)$results['db_used'];
}

	
	// Return the DBNAME as per the panel
	// e.g if dbname is given and a prefix is required then please give it here
	function dbname($dbname) {
        $prefix = $this->username.'_'; 
    return $prefix . $dbname;
}
	
	// Return the DBUSERNAME as per the panel
	// e.g if dbusername is given and a prefix is required then please give it here
	function dbuser($dbuser){
		 $prefix = $this->username.'_'; 
    return $prefix . $dbuser;
	}
	
	function dbexists($dbname){
    $parms = ['dbname' => $dbname];
    $response =  $this->olspanel->dbexists();
    
    // Expecting: {"exists": true/false}
    return !empty($response['exists']) && $response['exists'] === true;
}

function dbuserexists($dbuser){
    $parms = ['dbuser' => $dbuser];
    $response =  $this->olspanel->dbuserexists();
    
    // Expecting: {"exists": true/false}
    return !empty($response['exists']) && $response['exists'] === true;
}


function set_permission($full_path){
    $parms = ['full_path' => $full_path];
    $response =  $this->olspanel->set_permission($full_path);
    
    if (!empty($response['success']) && $response['success'] === true) {
        return true;
    }

    return false;
}
	
	//This will create a Database
function createdb($dbname, $dbuser, $dbpass, $type = 'mysql') {
    // Get the username prefix (optional, remove if not needed)
    $prefix = $this->username . '_';

    // Check if the dbname already contains the prefix and remove it if present
    if (strpos($dbname, $prefix) === 0) {
        $dbname = substr($dbname, strlen($prefix)); // Remove the prefix from the beginning
    }

    // Check if the dbuser already contains the prefix and remove it if present
    if (strpos($dbuser, $prefix) === 0) {
        $dbuser = substr($dbuser, strlen($prefix)); // Remove the prefix from the beginning
    }

    // Prepare the parameters to send to the API
    $parms = [
        'dbname'   => $dbname,
        'dbuser'   => $dbuser,
        'dbpass'   => $dbpass,
        'dbpassc'  => $dbpass
    ];

    // Call the API using your existing auth_me method
    $response =  $this->olspanel->db_make($dbname, $dbuser, $dbpass);

    // Check the API response
    if (!empty($response['success']) && $response['success'] === true) {
        return true;
    }

    return false;
}


	
	//Delete a Database and user
	function deldb($dbname, $dbuser, $type = 'mysql') {
		// $dbuser might not be auto-deleted because it may be connected to multiple databases

    $params = [
        'v' => 1,
        'action' => 'delete'
    ];

    $results =  $this->olspanel->db_delete($dbname);

    // Optionally check the response:
    if (isset($results['success'])) {
        return true;
    } else {
        // You can log or return error message if needed
        // error_log($results['error']);
        return false;
    }
}


function spaceremain(){
    // Call the authenticated API to get disk info
    $parms = ['v' => 1];
    $results = $this->olspanel->home();

   $disk_limit = $results['disk_limit'] ?? '∞';
    $disk_used  = $results['disk_used'] ?? '0 KB';

    // If disk_limit is ∞, treat it as unlimited
    if ($disk_limit === '∞') {
        $disk_limit = "100000 MB";  // Treat it as a large value if it's unlimited
    }else{
		$disk_limit = "$disk_limit MB";
	}

    // Convert human-readable size to bytes
	
  $limit_bytes = $this->convertToBytes($disk_limit);
  $used_bytes  = $this->convertToBytes($disk_used);

    // Calculate remaining space in bytes
    $remaining_bytes = $limit_bytes - $used_bytes;

    // Return the remaining space in bytes
    return $remaining_bytes;
}

private function convertToBytes($val) {
    
    $parts = explode(" ", $val);
    if (count($parts) != 2) {
      
        return 0;
    }

    $size = $parts[0];
    $unit = strtoupper($parts[1]);
    
     
    $num = floatval($size); // Convert the value to a number
    
    // Handle different units (KB, MB, GB) by converting everything to bytes
    switch ($unit) {
        case 'GB':  // GB
        
            return $num * 1024 * 1024 * 1024;  // Convert GB to bytes
        case 'MB':  // MB
           
            return $num * 1024 * 1024;         // Convert MB to bytes
        case 'KB':  // KB
           
            return $num * 1024;                // Convert KB to bytes
        default:    // Assume bytes if no unit is provided
          
            return $num; // Return as bytes if the value is already in bytes
    }
}






 


	
	// Add a CRON JOB
function addcron($min, $hour, $day, $month, $weekday, $command, $mail = '') {	
    $params = [
        'minute'  => $min,
        'hour'    => $hour,
        'day'     => $day,
        'month'   => $month,
        'weekday' => $weekday,
        'comm'    => $command
    ];

    $response =  $this->olspanel->addcron($min, $hour, $day, $month, $weekday, $command, $mail = '');

    if (isset($response['success']) && $response['success'] === true) {
        return true;
    } else {
        // Optionally log or return error
        return false;
    }
}

	
	function delcron($command) {
    // Step 1: Get line number from value
    $findParams = [
        'value' => $command
    ];
   $findResponse = $this->auth_me("cronjob_list/", $findParams);
 
    // Check if the line number was found
    if (!isset($findResponse['line_number'])) {
        // You can log or return an error
        // error_log("Cron job not found for command: " . $command);
        return false;
    }

    $lineNumber = $findResponse['line_number'];

    // Step 2: Call delete API
    $deleteParams = [
        'action' => 'delete'
    ];
    $deleteResponse = $this->auth_me("cronjob_delete/" . $lineNumber . "/", $deleteParams);

    // Check for success
    if (isset($deleteResponse['success'])) {
        return true;
    }

    // Optionally handle error
    // error_log($deleteResponse['error']);
    return false;
}

	
	
	// Lists the users details
	// $starting is for usernames starting with these characters
	// $limit if specified should return only that number of rows
	function listusers($starting = '', $limit = 0) {
    $baseDir = '/home/';
 
    $userArray = [];

    // Step 1: Get the list of users from /home directory
    $users = array_diff(scandir($baseDir), array('..', '.'));

    $count = 0;
    foreach ($users as $user) {
        // Skip excluded directories (vmail, olspanel)
        if (!is_dir($baseDir . $user) || in_array($user, ['vmail', 'olspanel'])) continue;

        // Construct email (assuming username@domain.com format)
        $email =$_COOKIE['email'];

        // Add user info to the array
        $userArray[$user]['softdir'] = $baseDir . $user;
        $userArray[$user]['email'] = $email;

        $count++;

        // If limit is set, break once we reach the limit
        if ($limit > 0 && $count >= $limit) break;
    }

    return $userArray;
}

	
	
}

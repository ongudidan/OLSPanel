<?php

class OLSPanel
{
    private $conn;
    private $user_id;
    private $user_data;
    private $package;
    private $username;
	
    public function __construct($username)
    {
        $this->username = $username;
		 //$this->username = 'babu';
        $this->connect();
        $this->loadUser();
        $this->loadPackage();
    }

    public function connect()
{
    $passFile = __DIR__ . "/etc/mysqlPassword";

    if (!is_readable($passFile)) {
        throw new Exception("MySQL password file not readable.");
    }

    $db_password = trim(file_get_contents($passFile));

    if (empty($db_password)) {
        throw new Exception("MySQL password file is empty.");
    }

    $this->conn = new mysqli(
        "localhost",
        "root",
        $db_password,
        "panel"
    );

    if ($this->conn->connect_error) {
        throw new Exception("Database connection failed: " . $this->conn->connect_error);
    }
}


    public function loadUser()
    {
        $stmt = $this->conn->prepare("SELECT * FROM auth_user WHERE username = ?");
        $stmt->bind_param("s", $this->username);
        $stmt->execute();
        $result = $stmt->get_result();

        if ($result->num_rows == 0) {
            throw new Exception("User not found.");
        }

        $this->user_data = $result->fetch_assoc();
        $this->user_id = $this->user_data['id'];

        $stmt->close();
		return $this->user_data;
    }

    public function loadPackage()
    {
        $stmt = $this->conn->prepare("
            SELECT p.* 
            FROM auth_user u
            JOIN packages p ON p.id = u.pkg_id
            WHERE u.id = ?
        ");
        $stmt->bind_param("i", $this->user_id);
        $stmt->execute();
        $result = $stmt->get_result();

        $this->package = $result->fetch_assoc();
        $stmt->close();
    }

    /* =======================
       HOME FUNCTION
    ======================== */

    public function home()
    {
        $disk = $this->getDiskUsage("/home/" . $this->username);
        $domain_count = $this->countDomains();
       
        $db_count = $this->countDatabases();

        return [
            'package_name' => $this->package['name'],
            'disk_limit'   => $this->package['disk_space'],
            'disk_used'    => $disk,
            
            'db_limit'     => $this->package['databases'],
            'db_used'      => $db_count,
          
            'domain_limit' => $this->package['allowed_domains'],
            'domain_used'  => $domain_count,
			'main_domain'  => $this->getMainDomain()
        ];
    }

    /* =======================
       DOMAIN LIST
    ======================== */

    public function domain_list()
    {
        $stmt = $this->conn->prepare("SELECT id, domain, path FROM domain WHERE userid = ?");
        $stmt->bind_param("i", $this->user_id);
        $stmt->execute();
        $result = $stmt->get_result();

        $domains = [];
        while ($row = $result->fetch_assoc()) {
            $domains[] = $row;
        }

        return $domains;
    }

public function getMainDomain()
{
    $stmt = $this->conn->prepare("
        SELECT domain 
        FROM domain 
        WHERE userid = ? 
        ORDER BY id ASC 
        LIMIT 1
    ");
    $stmt->bind_param("i", $this->user_id);
    $stmt->execute();

    $result = $stmt->get_result()->fetch_assoc();
    $stmt->close();

    return $result['domain'] ?? null;
}


   
   

    /* =======================
       DATABASE MAKE
    ======================== */

   public function db_make($dbname, $dbuser, $dbpass)
{
    $command = "/usr/local/bin/olspanel makedb " .
        "--username=" . escapeshellarg($this->username) . " " .
        "--dbname=" . escapeshellarg($dbname) . " " .
        "--dbuser=" . escapeshellarg($dbuser) . " " .
        "--dbpass=" . escapeshellarg($dbpass) . " " .
        "--dbpassc=" . escapeshellarg($dbpass) . " 2>&1";

    $output = shell_exec($command);

    return $this->extractJsonFromOutput($output);
}

public function db_delete($dbname)
{
    $command = "/usr/local/bin/olspanel dbedit " .
        "--username=" . escapeshellarg($this->username) . " " .
        "--db=" . escapeshellarg($dbname) . " " .
        "--action=delete 2>&1";

    $output = shell_exec($command);

    return $this->extractJsonFromOutput($output);
}


public function set_permission($full_path)
{
    $command = "/usr/local/bin/olspanel fixperm --username=" . escapeshellarg($this->username) . " --full_path=" . escapeshellarg($full_path) . " 2>&1";

    $output = shell_exec($command);

    return $this->extractJsonFromOutput($output);
}


public function addcron($min, $hour, $day, $month, $weekday, $command, $mail = '')
{
    // Build the CLI command
    $cliCommand = "/usr/local/bin/olspanel cronjob_add " .
        "--username=" . escapeshellarg($this->username) . " " .
        "--minute=" . escapeshellarg($min) . " " .
        "--hour=" . escapeshellarg($hour) . " " .
        "--day=" . escapeshellarg($day) . " " .
        "--month=" . escapeshellarg($month) . " " .
        "--weekday=" . escapeshellarg($weekday) . " " .
        "--comm=" . escapeshellarg($command) . " 2>&1";

    // Execute the command
    $output = shell_exec($cliCommand);

    // Parse and return JSON output
    return $this->extractJsonFromOutput($output);
}


    /* =======================
       HELPER FUNCTIONS
    ======================== */

    public function getDiskUsage($path)
    {
        $output = shell_exec("du -sh $path 2>/dev/null");
        return trim(explode("\t", $output)[0] ?? "0");
    }

    public function countDomains()
    {
        $stmt = $this->conn->prepare("SELECT COUNT(*) as total FROM domain WHERE userid = ?");
        $stmt->bind_param("i", $this->user_id);
        $stmt->execute();
        $result = $stmt->get_result()->fetch_assoc();
        return $result['total'];
    }
public function dbUserExists($dbuser)
{
    // Add username prefix if needed
    $prefix = $this->username . "_";
    if (strpos($dbuser, $prefix) !== 0) {
        $dbuser = $prefix . $dbuser;
    }

    // Prepare the query
    $stmt = $this->conn->prepare("SELECT COUNT(*) as total FROM mysql.user WHERE user = ?");
    $stmt->bind_param("s", $dbuser);
    $stmt->execute();
    $result = $stmt->get_result()->fetch_assoc();
    $stmt->close();

    // Return boolean like your previous style
    $response['exists'] = !empty($result['total']) && $result['total'] > 0;
    return !empty($response['exists']) && $response['exists'] === true;
}

public function dbExists($dbname)
{
    // Add username prefix if needed
    $prefix = $this->username . "_";
    if (strpos($dbname, $prefix) !== 0) {
        $dbname = $prefix . $dbname;
    }

    // Prepare the query to check if database exists
    $stmt = $this->conn->prepare("SELECT COUNT(*) as total FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = ?");
    $stmt->bind_param("s", $dbname);
    $stmt->execute();
    $result = $stmt->get_result()->fetch_assoc();
    $stmt->close();

    // Return boolean like your previous style
    $response['exists'] = !empty($result['total']) && $result['total'] > 0;
    return !empty($response['exists']) && $response['exists'] === true;
}



    public function countDatabases()
    {
        $prefix = $this->username . "_";
        $result = $this->conn->query("SHOW DATABASES LIKE '$prefix%'");
        return $result->num_rows;
    }

   
public function extractJsonFromOutput($rawOutput)
{
    if (empty($rawOutput)) {
        return false;
    }

    // Extract first JSON object found
    if (preg_match('/\{.*\}/s', $rawOutput, $matches)) {
        $jsonString = $matches[0];

        $decoded = json_decode($jsonString, true);

        if (json_last_error() === JSON_ERROR_NONE) {
            return $decoded;
        }
    }

    return false;
}

    public function domainExists($domain)
    {
        $stmt = $this->conn->prepare("SELECT id FROM domain WHERE domain = ?");
        $stmt->bind_param("s", $domain);
        $stmt->execute();
        return $stmt->get_result()->num_rows > 0;
    }
}
?>

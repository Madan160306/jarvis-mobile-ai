import socket
import time

class NetworkUtils:
    _last_check_time = 0
    _is_online = False
    _check_interval = 10 # seconds

    @classmethod
    def is_online(cls, force=False) -> bool:
        """
        Check if the device has active internet connectivity.
        Caches the result for _check_interval seconds to avoid slowing down commands.
        """
        current_time = time.time()
        
        # Return cached result if we checked recently, unless forced
        if not force and (current_time - cls._last_check_time < cls._check_interval):
            return cls._is_online
            
        try:
            # Connect to a reliable, highly available public DNS (Google's 8.8.8.8)
            # Timeout is very short (1 second) to ensure UI/Voice doesn't freeze
            sock = socket.create_connection(("8.8.8.8", 53), timeout=1.0)
            sock.close()
            cls._is_online = True
        except OSError:
            cls._is_online = False
            
        cls._last_check_time = current_time
        return cls._is_online

import socket
import time

class NetworkUtils:
    _last_check_time = 0
    _is_online = False
    _check_interval = 30 # seconds

    @classmethod
    def is_online(cls, force=False) -> bool:
        """
        Check if the device has active internet connectivity.
        Caches the result for 30 seconds to avoid slowing down commands.
        """
        current_time = time.time()
        
        if not force and (current_time - cls._last_check_time < cls._check_interval):
            return cls._is_online
            
        try:
            sock = socket.create_connection(("api.groq.com", 443), timeout=1.5)
            sock.close()
            cls._is_online = True
        except OSError:
            cls._is_online = False
            
        cls._last_check_time = current_time
        return cls._is_online

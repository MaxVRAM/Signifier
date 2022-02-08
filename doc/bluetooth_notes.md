# Bluetooth

Attempted several Bluetooth modules for Python

**TODO**: List here.


- Using the bleson Python module: <https://bleson.readthedocs.io/en/latest/index.html>

- Recommended to stop the Pi's bluetooth service:

  ```bash
  sudo service bluetooth stop
  ```

- Can use BLE commands without sudo!

  ```bash
  sudo setcap cap_net_raw,cap_net_admin+eip $(eval readlink -f `which python3`)
  ```


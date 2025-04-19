package com.example.offlinemesh;

import android.Manifest;
import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.view.View;
import android.widget.*;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import android.os.Build;
import android.provider.Settings;


import java.util.ArrayList;
import java.util.Set;

public class DeviceListActivity extends Activity {

    private BluetoothAdapter bluetoothAdapter;
    private ArrayAdapter<String> deviceListAdapter;
    private ArrayList<BluetoothDevice> devices = new ArrayList<>();

    private static final int REQUEST_PERMISSION = 101;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_device_list);

        ListView listView = findViewById(R.id.device_list);
        deviceListAdapter = new ArrayAdapter<>(this, android.R.layout.simple_list_item_1);
        listView.setAdapter(deviceListAdapter);

        bluetoothAdapter = BluetoothAdapter.getDefaultAdapter();

        // Ask for BLUETOOTH_SCAN if not granted
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            // Android 12+ needs BLUETOOTH_SCAN
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_SCAN)
                    != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this,
                        new String[]{Manifest.permission.BLUETOOTH_SCAN},
                        REQUEST_PERMISSION);
            } else {
                discoverDevices();
            }
        } else {
            // Older Android versions don't need this permission
            discoverDevices();
        }


        listView.setOnItemClickListener((parent, view, position, id) -> {
            BluetoothDevice selectedDevice = devices.get(position);
            Intent resultIntent = new Intent();
            resultIntent.putExtra("device_address", selectedDevice.getAddress());
            setResult(Activity.RESULT_OK, resultIntent);
            finish();
        });
    }

    private void discoverDevices() {
        deviceListAdapter.clear();
        devices.clear();

        // Already paired devices
        Set<BluetoothDevice> paired = bluetoothAdapter.getBondedDevices();
        if (paired != null) {
            for (BluetoothDevice device : paired) {
                devices.add(device);
                deviceListAdapter.add(device.getName() + "\n" + device.getAddress());
            }
        }

        // Register for discovered devices
        IntentFilter filter = new IntentFilter(BluetoothDevice.ACTION_FOUND);
        registerReceiver(receiver, filter);

        bluetoothAdapter.startDiscovery();
    }

    private final BroadcastReceiver receiver = new BroadcastReceiver() {
        public void onReceive(Context context, Intent intent) {
            if (BluetoothDevice.ACTION_FOUND.equals(intent.getAction())) {
                BluetoothDevice device = intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE);
                if (device != null && !devices.contains(device)) {
                    devices.add(device);
                    deviceListAdapter.add(device.getName() + "\n" + device.getAddress());
                }
            }
        }
    };

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (bluetoothAdapter != null && bluetoothAdapter.isDiscovering()) {
            bluetoothAdapter.cancelDiscovery();
        }
        unregisterReceiver(receiver);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);

        if (requestCode == REQUEST_PERMISSION) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                discoverDevices();
            } else {
                Toast.makeText(this, "Scan permission denied. Please enable it in settings.", Toast.LENGTH_LONG).show();
                // Don't finish(), let user retry or exit manually
            }
        }
    }

}

package com.example.offlinemesh;

import android.Manifest;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.os.Handler;
import android.widget.Button;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

public class MainActivity extends AppCompatActivity {

    private static final int REQUEST_ENABLE_BT = 1;
    private static final int REQUEST_PERMISSION = 1002;
    private static final int REQUEST_DEVICE_CONNECT = 2001;

    private BluetoothAdapter bluetoothAdapter;
    private BluetoothChatService chatService;

    private final Handler handler = new Handler(msg -> {
        switch (msg.what) {
            case BluetoothChatService.MESSAGE_CONNECTED:
                runOnUiThread(() -> {
                    chatService.setHandler(null); // detach handler
                    ChatActivity.setChatService(chatService);
                    Intent chatIntent = new Intent(MainActivity.this, ChatActivity.class);
                    chatIntent.putExtra("isServer", false);
                    startActivity(chatIntent);
                });
                break;

            case BluetoothChatService.MESSAGE_CONNECTION_FAILED:
                runOnUiThread(() -> Toast.makeText(MainActivity.this, "Connection Failed", Toast.LENGTH_SHORT).show());
                break;
        }
        return true;
    });

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        bluetoothAdapter = BluetoothAdapter.getDefaultAdapter();

        if (bluetoothAdapter == null) {
            Toast.makeText(this, "Bluetooth not supported", Toast.LENGTH_SHORT).show();
            finish();
            return;
        }

        // Initialize chatService here
        chatService = new BluetoothChatService(handler);

        // Check permissions
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_CONNECT)
                != PackageManager.PERMISSION_GRANTED ||
                ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_SCAN)
                        != PackageManager.PERMISSION_GRANTED) {

            ActivityCompat.requestPermissions(this, new String[]{
                    Manifest.permission.BLUETOOTH_CONNECT,
                    Manifest.permission.BLUETOOTH_SCAN,
                    Manifest.permission.ACCESS_FINE_LOCATION
            }, REQUEST_PERMISSION);
        } else {
            enableBluetoothIfNeeded();
        }

        Button findBtn = findViewById(R.id.find_devices_btn);
        findBtn.setOnClickListener(v -> {
            Intent intent = new Intent(MainActivity.this, DeviceListActivity.class);
            startActivityForResult(intent, REQUEST_DEVICE_CONNECT);
        });
    }

    private void enableBluetoothIfNeeded() {
        if (!bluetoothAdapter.isEnabled()) {
            Intent enableIntent = new Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE);
            startActivityForResult(enableIntent, REQUEST_ENABLE_BT);
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);

        if (requestCode == REQUEST_DEVICE_CONNECT && resultCode == RESULT_OK) {
            try {
                String deviceAddress = data.getStringExtra("device_address");
                Toast.makeText(this, "Selected: " + deviceAddress, Toast.LENGTH_SHORT).show();

                if (chatService == null) {
                    chatService = new BluetoothChatService(handler);
                }

                BluetoothDevice device = bluetoothAdapter.getRemoteDevice(deviceAddress);
                chatService.connect(device); // Connect, wait for handler to launch ChatActivity

            } catch (Exception e) {
                e.printStackTrace();
                Toast.makeText(this, "Error: " + e.getMessage(), Toast.LENGTH_LONG).show();
            }
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(requestCode, permissions, results);
        if (requestCode == REQUEST_PERMISSION) {
            if (results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED) {
                enableBluetoothIfNeeded();
            } else {
                Toast.makeText(this, "Bluetooth permissions required!", Toast.LENGTH_SHORT).show();
            }
        }
    }
}

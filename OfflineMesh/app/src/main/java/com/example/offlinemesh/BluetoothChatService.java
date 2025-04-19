package com.example.offlinemesh;

import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothServerSocket;
import android.bluetooth.BluetoothSocket;
import android.os.Handler;
import android.util.Log;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.UUID;

public class BluetoothChatService {

    public static final int MESSAGE_READ = 0;
    public static final int MESSAGE_WRITE = 1;
    public static final int MESSAGE_TOAST = 2;
    public static final int MESSAGE_CONNECTED = 3;
    public static final int MESSAGE_CONNECTION_FAILED = 4;

    private static final String TAG = "BluetoothChatService";
    private static final String APP_NAME = "OfflineMesh";
    private static final UUID MY_UUID = UUID.fromString("fa87c0d0-afac-11de-8a39-0800200c9a66");

    private final BluetoothAdapter adapter;
    private Handler handler;

    private AcceptThread acceptThread;
    private ConnectThread connectThread;
    private ConnectedThread connectedThread;

    public BluetoothChatService(Handler handler) {
        this.adapter = BluetoothAdapter.getDefaultAdapter();
        this.handler = handler;
        start();
    }

    public void setHandler(Handler handler) {
        this.handler = handler;
    }

    public synchronized void start() {
        if (connectThread != null) {
            connectThread.cancel();
            connectThread = null;
        }

        if (acceptThread == null) {
            acceptThread = new AcceptThread();
            acceptThread.start();
        }
    }

    public void stop() {
        if (connectThread != null) {
            connectThread.cancel();
            connectThread = null;
        }

        if (acceptThread != null) {
            acceptThread.cancel();
            acceptThread = null;
        }

        if (connectedThread != null) {
            connectedThread.cancel();
            connectedThread = null;
        }
    }

    public void connect(BluetoothDevice device) {
        if (connectThread != null) {
            connectThread.cancel();
        }
        connectThread = new ConnectThread(device);
        connectThread.start();
    }

    public void write(byte[] out) {
        ConnectedThread r;
        synchronized (this) {
            if (connectedThread == null) return;
            r = connectedThread;
        }
        r.write(out);
    }

    private class AcceptThread extends Thread {
        private final BluetoothServerSocket serverSocket;

        public AcceptThread() {
            BluetoothServerSocket tmp = null;
            try {
                tmp = adapter.listenUsingRfcommWithServiceRecord(APP_NAME, MY_UUID);
            } catch (IOException e) {
                Log.e(TAG, "AcceptThread listen failed", e);
            }
            serverSocket = tmp;
        }

        public void run() {
            BluetoothSocket socket;
            while (true) {
                try {
                    socket = serverSocket.accept();
                } catch (IOException e) {
                    Log.e(TAG, "AcceptThread accept() failed", e);
                    handler.obtainMessage(MESSAGE_CONNECTION_FAILED).sendToTarget();
                    break;
                }

                if (socket != null) {
                    manageConnectedSocket(socket);
                    handler.obtainMessage(MESSAGE_CONNECTED).sendToTarget();
                    try {
                        serverSocket.close();
                    } catch (IOException e) {
                        Log.e(TAG, "Could not close server socket", e);
                    }
                    break;
                }
            }
        }

        public void cancel() {
            try {
                serverSocket.close();
            } catch (IOException e) {
                Log.e(TAG, "AcceptThread cancel failed", e);
            }
        }
    }

    private class ConnectThread extends Thread {
        private final BluetoothSocket socket;
        private final BluetoothDevice device;

        public ConnectThread(BluetoothDevice device) {
            BluetoothSocket tmp = null;
            this.device = device;

            try {
                tmp = device.createRfcommSocketToServiceRecord(MY_UUID);
            } catch (IOException e) {
                Log.e(TAG, "ConnectThread: Socket creation failed", e);
            }

            socket = tmp;
        }

        public void run() {
            adapter.cancelDiscovery();

            try {
                socket.connect();
                manageConnectedSocket(socket);
                handler.obtainMessage(MESSAGE_CONNECTED).sendToTarget();
            } catch (IOException connectException) {
                Log.e(TAG, "ConnectThread: Unable to connect", connectException);
                handler.obtainMessage(MESSAGE_CONNECTION_FAILED).sendToTarget();
                try {
                    socket.close();
                } catch (IOException closeException) {
                    Log.e(TAG, "Could not close client socket", closeException);
                }
            }
        }

        public void cancel() {
            try {
                socket.close();
            } catch (IOException e) {
                Log.e(TAG, "ConnectThread cancel failed", e);
            }
        }
    }

    private void manageConnectedSocket(BluetoothSocket socket) {
        if (connectedThread != null) {
            connectedThread.cancel();
        }
        connectedThread = new ConnectedThread(socket);
        connectedThread.start();
    }

    private class ConnectedThread extends Thread {
        private final BluetoothSocket socket;
        private final InputStream inStream;
        private final OutputStream outStream;

        public ConnectedThread(BluetoothSocket socket) {
            this.socket = socket;
            InputStream tmpIn = null;
            OutputStream tmpOut = null;

            try {
                tmpIn = socket.getInputStream();
                tmpOut = socket.getOutputStream();
            } catch (IOException e) {
                Log.e(TAG, "Error getting streams", e);
            }

            inStream = tmpIn;
            outStream = tmpOut;
        }

        public void run() {
            byte[] buffer = new byte[1024];
            int bytes;

            while (true) {
                try {
                    bytes = inStream.read(buffer);
                    handler.obtainMessage(MESSAGE_READ, bytes, -1, buffer.clone()).sendToTarget();
                } catch (IOException e) {
                    Log.e(TAG, "Connection lost", e);
                    break;
                }
            }
        }

        public void write(byte[] bytes) {
            try {
                outStream.write(bytes);
                handler.obtainMessage(MESSAGE_WRITE, -1, -1, bytes).sendToTarget();
            } catch (IOException e) {
                Log.e(TAG, "Write failed", e);
            }
        }

        public void cancel() {
            try {
                socket.close();
            } catch (IOException e) {
                Log.e(TAG, "Socket close failed", e);
            }
        }
    }

}

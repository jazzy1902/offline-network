package com.example.offlinemesh;

import android.os.Bundle;
import android.os.Handler;
import android.view.Gravity;
import android.view.LayoutInflater;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;

public class ChatActivity extends AppCompatActivity {

    private static BluetoothChatService chatService;
    private LinearLayout chatContainer;
    private ScrollView scrollView;
    private EditText inputField;
    private Button sendBtn;

    public static void setChatService(BluetoothChatService service) {
        chatService = service;
    }

    private final Handler handler = new Handler(msg -> {
        switch (msg.what) {
            case BluetoothChatService.MESSAGE_READ:
                byte[] readBuf = (byte[]) msg.obj;
                String received = new String(readBuf, 0, msg.arg1);
                addMessage(received, false);
                break;
            case BluetoothChatService.MESSAGE_WRITE:
                byte[] writeBuf = (byte[]) msg.obj;
                String sent = new String(writeBuf);
                addMessage(sent, true);
                break;
        }
        return true;
    });

    private void addMessage(String message, boolean isSent) {
        LayoutInflater inflater = LayoutInflater.from(this);
        View messageView = inflater.inflate(R.layout.message_bubble, chatContainer, false);
        
        TextView messageText = messageView.findViewById(R.id.message_text);
        messageText.setText(message);
        
        LinearLayout messageContainer = messageView.findViewById(R.id.message_container);
        LinearLayout.LayoutParams params = (LinearLayout.LayoutParams) messageContainer.getLayoutParams();
        
        if (isSent) {
            params.gravity = Gravity.END;
            messageContainer.setBackground(ContextCompat.getDrawable(this, R.drawable.sent_message_bg));
        } else {
            params.gravity = Gravity.START;
            messageContainer.setBackground(ContextCompat.getDrawable(this, R.drawable.received_message_bg));
        }
        
        messageContainer.setLayoutParams(params);
        chatContainer.addView(messageView);
        
        // Scroll to bottom
        scrollView.post(() -> scrollView.fullScroll(View.FOCUS_DOWN));
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_chat);

        chatContainer = findViewById(R.id.chat_container);
        scrollView = findViewById(R.id.scroll_view);
        inputField = findViewById(R.id.message_input);
        sendBtn = findViewById(R.id.send_btn);

        if (chatService == null) {
            Toast.makeText(this, "Chat service is null. Cannot proceed.", Toast.LENGTH_LONG).show();
            finish();
            return;
        }

        chatService.setHandler(handler);

        boolean isServer = getIntent().getBooleanExtra("isServer", true);
        if (isServer) {
            chatService.start(); // Server waits for connection
        }

        sendBtn.setOnClickListener(v -> {
            String msg = inputField.getText().toString().trim();
            if (!msg.isEmpty()) {
                chatService.write(msg.getBytes());
                inputField.setText("");
            }
        });
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (chatService != null) {
            chatService.setHandler(null); // prevent memory leaks
        }
    }
}

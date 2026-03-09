
// <AUTO_BLOCKS>
// --- 速度 PI 控制程序块 ---
float speed_err = speed_ref - speed_feedback;
g_speed_integral += speed_err;
float speed_out = g_speed_kp * speed_err + g_speed_ki * g_speed_integral;

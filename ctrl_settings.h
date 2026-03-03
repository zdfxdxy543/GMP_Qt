/*
 * ctrl_settings.h
 * 电机控制器配置参数
 * 自动生成，请勿手动修改
 */

#ifndef CTRL_SETTINGS_H
#define CTRL_SETTINGS_H

// 调试选项
#define BUILD_LEVEL (1)

// 控制器基本参数
#define CTRL_STARTUP_DELAY (1000)  // 控制器启动延时（ms）
#define CONTROLLER_FREQUENCY (20e3)        // 控制器工作频率（Hz）
#define CTRL_PWM_CMP_MAX (2499)        // PWM比较最大值（%）
#define CTRL_PWM_DEADBAND_CMP (10)     // PWM死区（%）
#define DSP_C2000_DSP_TIME_DIV (10000)      // 系统时钟周期（ns）
#define CTRL_ADC_VOLTAGE_REF (3.3f)     // 控制器ADC参考电压（V）

// 硬件参数
#define BOOSTXL_3PHGANINV_IS_DEFAULT_PARAM // 是否启用平滑电流控制
#include <E:/Related_Github_Project/GMP_Qt/ctrl_settings.h> // invoke motor parameters
#include <E:/Related_Github_Project/GMP_Qt/ctrl_settings.h> // invoke motor controller parameters

// 编码器参数
#define CTRL_POS_ENC_FS (4096)      // 编码器满量程值
#define CTRL_POS_ENC_BIAS (2048)               // 电机控制器偏置值
#define CTRL_SPD_DIV (5)          // 速度划分值
#define CTRL_POS_DIV (5)       // 位置划分值

// 电机控制器基值
#define CTRL_DCBUS_VOLTAGE (12.0f)   // 直流母线电压值
#define CTRL_VOLTAGE_BASE (4.0f)    // 三相电压值
#define CTRL_CURRENT_BASE (1.0f)      // 电流基准值

#define CTRL_INVERTER_CURRENT_SENSITIVITY (MY_BOARD_PH_SHUNT_RESISTANCE_OHM * MY_BOARD_PH_CSA_GAIN_V_V) // 逆变器电流灵敏度
#define CTRL_INVERTER_CURRENT_BIAS (MY_BOARD_PH_CSA_BIAS_V) // 逆变器电流偏置值
#define CTRL_INVERTER_VOLTAGE_SENSITIVITY (MY_BOARD_PH_VOLTAGE_SENSE_GAIN) // 逆变器电压灵敏度
#define CTRL_INVERTER_VOLTAGE_BIAS (MY_BOARD_PH_VOLTAGE_SENSE_BIAS_V) // 逆变器电压偏置值

#define CTRL_DC_CURRENT_SENSITIVITY (MY_BOARD_DCBUS_CURRENT_SENSE_GAIN) // 直流母线电流灵敏度
#define CTRL_DC_CURRENT_BIAS (MY_BOARD_DCBUS_CURRENT_SENSE_BIAS_V) // 直流母线电流偏置值
#define CTRL_DC_VOLTAGE_SENSITIVITY (MY_BOARD_DCBUS_VOLTAGE_SENSE_GAIN) // 直流母线电压灵敏度
#define CTRL_DC_VOLTAGE_BIAS (MY_BOARD_DCBUS_VOLTAGE_SENSE_BIAS_V) // 直流母线电压偏置值

// 电机控制器参数
#define _USE_DEBUG_DISCRETE_PID      // 是否使用离散PID控制器
#define PWM_MODULATOR_USING_NEGATIVE_LOGIC (1)         // 是否使用负电流调制
#define TIMEOUT_ADC_CALIB_MS (1000)            // ADC校准超时时间（ms）
#define MC_CURRENT_SAMPLE_PHASE_MODE (2)    // 电流采样相位模式
#define ENABLE_MOTOR_FAULT_PROTECTION         // 是否启用电机故障保护
#define ENABLE_SMO         // 是否启用平滑电流控制

// QEP encoder channel
#define EQEP_Encoder_BASE EQEP2_J13_BASE


// System LED
#define SYSTEM_LED     LED_R
#define CONTROLLER_LED LED_G


// PWM Channels
#define PHASE_U_BASE EPWM_J4_PHASE_U_BASE
#define PHASE_V_BASE EPWM_J4_PHASE_V_BASE
#define PHASE_W_BASE EPWM_J4_PHASE_W_BASE


// PWM Enable
#define PWM_ENABLE_PORT ENABLE_GATE
#define PWM_RESET_PORT  RESET_GATE


// DC Bus Voltage & Current
#define INV_VBUS J3_VDC
#define INV_IBUS


#define INV_VBUS_RESULT_BASE J3_VDC_RESULT_BASE
#define INV_IBUS_RESULT_BASE


// Inverter side Voltage & Current
#define INV_IU J3_IU
#define INV_IV J3_IV
#define INV_IW J3_IW


#define INV_IU_RESULT_BASE J3_IU_RESULT_BASE
#define INV_IV_RESULT_BASE J3_IV_RESULT_BASE
#define INV_IW_RESULT_BASE J3_IW_RESULT_BASE


#define INV_UU J3_VU
#define INV_UV J3_VV
#define INV_UW J3_VW


#define INV_UU_RESULT_BASE J3_VU_RESULT_BASE
#define INV_UV_RESULT_BASE J3_VV_RESULT_BASE
#define INV_UW_RESULT_BASE J3_VW_RESULT_BASE

#endif /* CTRL_SETTINGS_H */

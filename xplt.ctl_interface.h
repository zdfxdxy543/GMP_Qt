// GMP core config module
#include <xplt.peripheral.h>

#ifndef _FILE_CTL_INTERFACE_H_
#define _FILE_CTL_INTERFACE_H_

#ifdef __cplusplus
extern "C"
{
#endif // __cplusplus

//BEGINDECLARATION

float g_current_limit = 18.0f;
//ENDDECLARATION

// Controller interface
// Input Callbacks
GMP_STATIC_INLINE void ctl_input_callback(void)
{

}

// Output Callbacks
GMP_STATIC_INLINE void ctl_output_callback(void)
{

}

// Function prototype
void GPIO_WritePin(uint16_t gpioNumber, uint16_t outVal);

// Enable Output
GMP_STATIC_INLINE void ctl_fast_enable_output()
{

}

// Disable Output
GMP_STATIC_INLINE void ctl_fast_disable_output()
{

}

#ifdef __cplusplus
}
#endif // __cplusplus

#endif // _FILE_CTL_INTERFACE_H_

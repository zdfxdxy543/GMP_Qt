// GMP core config module
#include <xplt.peripheral.h>

#ifndef _FILE_CTL_INTERFACE_H_
#define _FILE_CTL_INTERFACE_H_

#ifdef __cplusplus
extern "C"
{
#endif // __cplusplus

//BEGINDECLARATION


extern adc_gt uuvw_src[3];
//ENDDECLARATION

// Controller interface
// Input Callbacks
GMP_STATIC_INLINE void ctl_input_callback(void)
{
	uuvw_src[phase_U] = ADC_readResult(INV_UU_RESULT_BASE, INV_UU);
	uuvw_src[phase_V] = ADC_readResult(INV_UV_RESULT_BASE, INV_UV);
	uuvw_src[phase_W] = ADC_readResult(INV_UW_RESULT_BASE, INV_UW);

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
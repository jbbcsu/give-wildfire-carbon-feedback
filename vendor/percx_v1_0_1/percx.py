import numpy as np

def PFC_species_response(dT, t, A_CO2, A_CH4, tau, C_init, decay_rate):
    """
    Compute permafrost carbon loss response to temperature change.
    
    Parameters:
        dT (array): Temperature anomaly time series (relative to baseline).
        t (array): Corresponding time points.
        A_CO2 (float): Amplitude factor for CO2 release.
        tau (float): Characteristic timescale for CO2 and CH4 release (years).
        A_CH4 (float): Amplitude factor for CH4 release.
    
    Returns:
        C_CO2 (array): Carbon release as CO2 over time.
        C_CH4 (array): Carbon release as CH4 over time.
    """
    #dt = np.mean(np.diff(t))  # Time step size
    C_CO2 = np.zeros_like(dT)
    C_CH4 = np.zeros_like(dT)

    #gamma = 0.002   # Amplitude decay factor

    # Initialize remaining carbon pool
    C_pool = C_init   # PgC

    for i in range(len(t)):
        # Compute potential emissions without constraint
        dC_CO2 = np.sum(A_CO2 * dT[:i+1] * np.exp(-(t[i] - t[:i+1]) / tau))
        dC_CH4 = np.sum(A_CH4 * dT[:i+1] * np.exp(-(t[i] - t[:i+1]) / tau))

        # Apply decay-based constraint: emissions are scaled by remaining carbon pool
        dC_CO2 *= (C_pool / C_init)
        dC_CH4 *= (C_pool / C_init)
        
        # Ensure we don't exceed available carbon pool
        total_emission = dC_CO2 + dC_CH4
        if total_emission > C_pool:
            scale_factor = C_pool / total_emission
            dC_CO2 *= scale_factor
            dC_CH4 *= scale_factor

        # Update emissions and deplete the carbon pool
        C_CO2[i] = dC_CO2
        C_CH4[i] = dC_CH4
        C_pool -= (dC_CO2 + dC_CH4)  # Reduce available carbon

        # Ensure carbon pool does not go negative
        C_pool = max(C_pool, 0)
    
    return C_CO2, C_CH4


def PFC_combined_response(dT, time, A_CO2, A_CH4, tau, C_max, decay_rate):
    C_CO2, C_CH4 = PFC_species_response(dT, time, A_CO2, A_CH4, tau, C_max, decay_rate)
    return C_CO2 + C_CH4  # Total carbon loss
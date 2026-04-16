import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

def generate_publication_plot(df, particle_name="J/ψ", expected_mass=3.096, mass_range=(2.0, 5.0)):
    """
    Generates a high-quality Matplotlib plot for physics analysis.
    Returns a BytesIO object containing the PNG data.
    """
    # Use the calculated mass if it exists, otherwise use 'M'
    mass_col = 'Calculated_M' if 'Calculated_M' in df.columns else ('M' if 'M' in df.columns else None)
    
    if mass_col is None:
        raise ValueError("Dataframe must contain 'Calculated_M' or 'M' column.")

    # Create the plot
    fig = plt.figure(figsize=(10, 6))
    
    plt.hist(df[mass_col], bins=200, range=mass_range, color='royalblue', edgecolor='none')
    
    plt.title(f'Invariant Mass of Dimuon Pairs ({particle_name} → μμ)', fontsize=16)
    plt.xlabel('Invariant Mass [GeV/c²]', fontsize=14)
    plt.ylabel('Number of Events', fontsize=14)
    
    # Adding a text box or line pointing to the exact mass
    plt.axvline(x=expected_mass, color='red', linestyle='--', label=f'{particle_name} Mass ({expected_mass:.3f} GeV/c²)')
    plt.legend(fontsize=12)
    
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    # Save to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300)
    buf.seek(0)
    plt.close(fig)
    return buf

if __name__ == "__main__":
    # Maintain legacy CLI behavior
    print("Running standalone plot generation...")
    df = pd.read_csv('data/Jpsimumu_Run2011A.csv')
    
    # Simple manual mass calculation for demo
    if 'Calculated_M' not in df.columns:
        M2 = (df['E1'] + df['E2'])**2 - (df['px1'] + df['px2'])**2 - (df['py1'] + df['py2'])**2 - (df['pz1'] + df['pz2'])**2
        df['Calculated_M'] = np.sqrt(np.maximum(M2, 0))
    
    plot_buf = generate_publication_plot(df)
    with open('Jpsi_mass_histogram.png', 'wb') as f:
        f.write(plot_buf.getbuffer())
    print("Plot saved successfully as Jpsi_mass_histogram.png!")

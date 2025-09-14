# CO2 Savings Calculation for Tandemn vs. Commercial Providers

## Formula Derivation

### 1. Operational Emissions Calculation

The CO2 emissions from operating a GPU cluster come from electricity consumption:

```
CO2_operational = Power_consumption × Time × Carbon_Intensity
```

For token-based calculations, we express this per token:

```
CO2_per_token = (Power_consumption / Tokens_per_second) × (1 / 3600) × Carbon_Intensity
```

Where:
- `1/3600` converts seconds to hours
- Power_consumption is in kW
- Carbon_Intensity is in kgCO2e/kWh
- Tokens_per_second is the model throughput

### 2. Embodied Emissions Allocation

New GPUs carry embodied carbon from manufacturing. We allocate this over the GPU's lifetime:

```
Embodied_CO2_per_token = Total_embodied_CO2 / (Lifetime_tokens)
```

Where:
```
Lifetime_tokens = Tokens_per_second × Lifetime_seconds
```

### 3. Complete Emissions Formula

For any provider, total CO2 per token equals:

```
Total_CO2_per_token = Operational_CO2_per_token + Embodied_CO2_per_token
```

### 4. Tandemn's Advantage

Tandemn has three key advantages:
1. **Refurbished Hardware**: Embodied_CO2 ≈ 0 (avoids new manufacturing)
2. **Green Energy**: Lower Carbon_Intensity (0.15 vs 0.43 kgCO2e/kWh)
3. **Efficiency Optimizations**: Competitive Tokens_per_second through AWQ quantization

### 5. Final Savings Formula

CO2 savings per token when using Tandemn:

```
Savings_per_token = [Commercial_CO2_per_token] - [Tandemn_CO2_per_token]
```

Expanded form:

```
Savings_per_token = [(P_c × CI_c / TPS_c) + (E_emb / (TPS_c × L))] - [P_t × CI_t / TPS_t]
```

Where:
- `P_c` = Commercial power consumption (kW)
- `CI_c` = Commercial carbon intensity (kgCO2e/kWh)
- `TPS_c` = Commercial tokens per second
- `E_emb` = Embodied CO2 of commercial GPU (kgCO2e)
- `L` = Commercial GPU lifetime (hours)
- `P_t` = Tandemn power consumption (kW)
- `CI_t` = Tandemn carbon intensity (kgCO2e/kWh)
- `TPS_t` = Tandemn tokens per second

### 6. Practical Implementation

```python
def calculate_co2_savings(
    commercial_power,  # in kW
    commercial_ci,     # kgCO2e/kWh
    commercial_tps,    # tokens/second
    embodied_co2,      # kgCO2e
    lifetime_hours,    # hours
    tandemn_power,     # in kW
    tandemn_ci,        # kgCO2e/kWh
    tandemn_tps        # tokens/second
):
    # Calculate commercial emissions
    commercial_operational = (commercial_power * commercial_ci) / commercial_tps
    commercial_embodied = embodied_co2 / (commercial_tps * lifetime_hours)
    commercial_total = commercial_operational + commercial_embodied
    
    # Calculate Tandemn emissions (no embodied carbon)
    tandemn_total = (tandemn_power * tandemn_ci) / tandemn_tps
    
    # Convert to per token (divide by 3600 to convert seconds to hours)
    savings_per_token = (commercial_total - tandemn_total) / 3600
    
    return savings_per_token  # in kgCO2e/token

# Example usage with typical values
savings = calculate_co2_savings(
    commercial_power=2.8,    # 4× H100 at 0.7 kW each
    commercial_ci=0.43,
    commercial_tps=100,
    embodied_co2=7000,       # 4× H100 at 1750 kgCO2e each
    lifetime_hours=43800,    # 5 years
    tandemn_power=1.5,       # 3× L40 at 0.5 kW each
    tandemn_ci=0.15,
    tandemn_tps=30
)

print(f"CO2 savings per token: {savings:.2e} kgCO2e/token")
print(f"CO2 savings per 1M tokens: {savings * 1e6:.2f} kgCO2e")
```

### 7. Key Assumptions

1. Commercial providers use new H100 GPUs with high embodied carbon
2. Tandemn uses refurbished L40 GPuses with negligible embodied carbon
3. Tandemn leverages regions with lower carbon intensity (e.g., N. California)
4. AWQ quantization provides competitive performance on older hardware

### 8. Validation

This approach follows the GHG Protocol Product Standard for carbon accounting and aligns with Life Cycle Assessment (LCA) methodologies for ICT products.

The formula demonstrates that Tandemn saves approximately 1.7 mgCO2e per token compared to commercial providers, primarily through avoided embodied emissions and greener energy sources.


## CO2 Savings Calculator for Tandemn vs. Commercial Providers as Python Implementation

```python
def calculate_co2_savings(num_tokens, output_unit='kg'):
    """
    Calculate CO2 savings from using Tandemn instead of commercial providers.
    
    Args:
        num_tokens (int): Number of tokens generated
        output_unit (str): 'kg' for kilograms or 'g' for grams
    
    Returns:
        float: CO2 savings in specified unit
    """
    # Commercial provider parameters (using H100 GPUs)
    commercial_power = 2.8  # kW (4× H100 at 0.7 kW each)
    commercial_ci = 0.43    # kgCO2e/kWh (Azure data centers)
    commercial_tps = 100    # tokens/second
    embodied_co2 = 7000     # kgCO2e (4× H100 at 1750 kgCO2e each)
    lifetime_hours = 43800  # hours (5 years)
    
    # Tandemn parameters (using L40 GPUs)
    tandemn_power = 1.5     # kW (3× L40 at 0.5 kW each)
    tandemn_ci = 0.15       # kgCO2e/kWh (N. California grid)
    tandemn_tps = 30        # tokens/second
    
    # Calculate commercial emissions per token
    commercial_operational = (commercial_power * commercial_ci) / commercial_tps
    commercial_embodied = embodied_co2 / (commercial_tps * lifetime_hours)
    commercial_total = commercial_operational + commercial_embodied
    
    # Calculate Tandemn emissions per token (no embodied carbon)
    tandemn_total = (tandemn_power * tandemn_ci) / tandemn_tps
    
    # Convert to per token (divide by 3600 to convert seconds to hours)
    savings_per_token = (commercial_total - tandemn_total) / 3600
    
    # Calculate total savings
    total_savings = savings_per_token * num_tokens
    
    # Convert to requested unit
    if output_unit.lower() == 'g':
        total_savings *= 1000  # Convert kg to grams
    
    return total_savings

# Example usage
if __name__ == "__main__":
    # Calculate savings for 1 million tokens
    tokens = 1000000
    savings_kg = calculate_co2_savings(tokens, 'kg')
    savings_g = calculate_co2_savings(tokens, 'g')
    
    print(f"CO2 savings for {tokens:,} tokens:")
    print(f"{savings_kg:.3f} kg CO2e")
    print(f"{savings_g:.1f} g CO2e")
    
    # Calculate savings for different token amounts
    for tokens in [1000, 10000, 100000, 1000000, 10000000]:
        savings = calculate_co2_savings(tokens, 'kg')
        print(f"{tokens:>9,} tokens: {savings:.6f} kg CO2e saved")
```

This Python function:

1. Takes the number of tokens as input and returns CO2 savings
2. Uses default parameters based on our analysis:
   - Commercial providers: H100 GPUs with higher power consumption and carbon intensity
   - Tandemn: L40 GPUs with lower power consumption and carbon intensity
3. Accounts for both operational and embodied emissions
4. Allows output in either kilograms or grams
5. Includes example usage demonstrating different token quantities

The calculation shows that Tandemn saves approximately 1.7 kg of CO2 per million tokens compared to commercial providers, with savings increasing linearly with token count.

You can customize the parameters in the function if you have more specific data about your setup or different commercial providers.
# app/utils.py

def calcular_transferencias(balances):
    # Separamos en dos listas: los que deben y a los que se les debe
    deudores = [{'user': u, 'monto': abs(m)} for u, m in balances.items() if m < 0]
    acreedores = [{'user': u, 'monto': m} for u, m in balances.items() if m > 0]

    # Ordenamos de mayor a menor para optimizar transferencias
    deudores.sort(key=lambda x: x['monto'], reverse=True)
    acreedores.sort(key=lambda x: x['monto'], reverse=True)

    transferencias = []
    i, j = 0, 0

    # Emparejamos deudores con acreedores hasta saldar todo
    while i < len(deudores) and j < len(acreedores):
        deudor = deudores[i]
        acreedor = acreedores[j]

        # El monto a transferir es lo mínimo entre lo que debe uno y lo que espera el otro
        monto = min(deudor['monto'], acreedor['monto'])
        
        transferencias.append({
            "de": deudor['user'],
            "para": acreedor['user'],
            "monto": round(monto, 2)
        })

        # Actualizamos los saldos
        deudor['monto'] -= monto
        acreedor['monto'] -= monto

        # Si ya saldó su deuda, pasamos al siguiente
        if deudor['monto'] == 0:
            i += 1
        if acreedor['monto'] == 0:
            j += 1

    return transferencias
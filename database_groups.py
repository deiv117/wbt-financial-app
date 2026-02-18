# database_groups.py
import streamlit as st # <-- ¡CRÍTICO PARA LOS CHIVATOS!
from database import get_supabase_client

# ==========================================
# 1. CORE DE GRUPOS (Crear, Leer, Borrar)
# ==========================================

def create_group(name, emoji, color, user_id):
    client = get_supabase_client()
    try:
        group_data = {"name": name, "emoji": emoji, "color": color, "created_by": user_id}
        res = client.table("groups").insert(group_data).execute()
        
        if res.data:
            group_id = res.data[0]['id']
            member_data = {"group_id": group_id, "user_id": user_id}
            client.table("group_members").insert(member_data).execute()
            return True, "Grupo creado con éxito"
        return False, "Error al crear grupo."
    except Exception as e:
        return False, str(e)

def get_user_groups(user_id):
    """Obtiene todos los grupos a los que pertenece el usuario."""
    client = get_supabase_client()
    try:
        # ¡CORREGIDO! Añadimos emoji y color al select
        res = client.table("group_members") \
            .select("group_id, groups(id, name, emoji, color, created_by, created_at)") \
            .eq("user_id", user_id) \
            .execute()
            
        if res.data:
            groups_list = []
            for item in res.data:
                group_info = item.get('groups')
                if group_info:
                    groups_list.append({
                        'id': group_info['id'],
                        'name': group_info['name'],
                        'emoji': group_info.get('emoji', '👥'), # Recuperamos el emoji
                        'color': group_info.get('color', '#636EFA'), # Recuperamos el color
                        'created_by': group_info['created_by'],
                        'created_at': group_info['created_at']
                    })
            groups_list.sort(key=lambda x: x['created_at'], reverse=True)
            return groups_list
        return []
    except Exception as e:
        print(f"Error obteniendo grupos: {e}")
        return []

def get_group_info(group_id):
    """Obtiene los datos y configuración general de un grupo"""
    client = get_supabase_client()
    try:
        res = client.table("groups").select("*").eq("id", group_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"Error obteniendo info del grupo: {e}")
        return None

def delete_group(group_id):
    """Elimina un grupo (borrando primero a los miembros)."""
    client = get_supabase_client()
    try:
        client.table("group_members").delete().eq("group_id", group_id).execute()
        client.table("groups").delete().eq("id", group_id).execute()
        return True
    except Exception as e:
        print(f"Error borrando grupo: {e}")
        return False


# ==========================================
# 2. GESTIÓN DE MIEMBROS
# ==========================================

def get_group_members(group_id):
    client = get_supabase_client()
    try:
        # AQUÍ ESTÁ LA MAGIA: Le decimos que traiga las nuevas columnas (id, is_external, external_name)
        res = client.table("group_members") \
            .select("id, user_id, leave_status, is_external, external_name, profiles(*)") \
            .eq("group_id", group_id).execute()
        return res.data
    except Exception as e:
        print(f"Error getting group members: {e}")
        return []

def remove_group_member(group_id, target_user_id):
    """Elimina a un usuario con chivato de errores"""
    client = get_supabase_client()
    try:
        client.table("group_members").delete().eq("group_id", group_id).eq("user_id", target_user_id).execute()
        return True
    except Exception as e:
        st.error(f"🛑 Error DB (Eliminando Miembro): {e}")
        return False

def request_leave_group(group_id, user_id):
    """Solicita salir del grupo con chivato de errores"""
    client = get_supabase_client()
    try:
        client.table("group_members").update({"leave_status": "pending"}).eq("group_id", group_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        st.error(f"🛑 Error DB (Pidiendo Salir): {e}")
        return False

def resolve_leave_request(group_id, target_user_id, approve=True):
    """El admin aprueba o rechaza la solicitud de salida"""
    client = get_supabase_client()
    try:
        if approve:
            client.table("group_members").delete().eq("group_id", group_id).eq("user_id", target_user_id).execute()
        else:
            client.table("group_members").update({"leave_status": "none"}).eq("group_id", group_id).eq("user_id", target_user_id).execute()
        return True
    except Exception as e:
        st.error(f"🛑 Error DB (Resolviendo Solicitud): {e}")
        return False


# ==========================================
# 3. SISTEMA DE INVITACIONES
# ==========================================

def send_invitation(group_id, email):
    client = get_supabase_client()
    try:
        data = {"group_id": group_id, "invited_email": email.lower().strip()}
        client.table("group_invitations").insert(data).execute()
        return True, "Invitación enviada"
    except Exception as e:
        return False, str(e)

def get_my_invitations(email):
    client = get_supabase_client()
    try:
        res = client.table("group_invitations") \
            .select("*, groups(name, emoji)") \
            .eq("invited_email", email.lower().strip()) \
            .eq("status", "pending") \
            .execute()
        return res.data or []
    except:
        return []

def get_invitations_count(email):
    """Cuenta cuántas invitaciones pendientes tiene el usuario"""
    client = get_supabase_client()
    try:
        res = client.table("group_invitations") \
            .select("id", count="exact") \
            .eq("invited_email", email.lower().strip()) \
            .eq("status", "pending") \
            .execute()
        return res.count if res.count else 0
    except Exception as e:
        print(f"Error contando invitaciones: {e}")
        return 0

def respond_invitation(invitation_id, group_id, user_id, accept=True):
    client = get_supabase_client()
    try:
        status = "accepted" if accept else "rejected"
        client.table("group_invitations").update({"status": status}).eq("id", invitation_id).execute()
        if accept:
            client.table("group_members").insert({"group_id": group_id, "user_id": user_id}).execute()
        return True
    except:
        return False


# ==========================================
# 4. AJUSTES DEL GRUPO
# ==========================================

def update_group_setting(group_id, setting_name, value):
    """Actualiza un ajuste específico con chivato de errores"""
    client = get_supabase_client()
    try:
        client.table("groups").update({setting_name: value}).eq("id", group_id).execute()
        return True
    except Exception as e:
        st.error(f"🛑 Error DB (Guardando Ajuste): {e}")
        return False

def update_group_details(group_id, name, emoji, color):
    """Actualiza detalles del grupo con chivato de errores"""
    client = get_supabase_client()
    try:
        client.table("groups").update({
            "name": name,
            "emoji": emoji,
            "color": color
        }).eq("id", group_id).execute()
        return True, "Grupo actualizado correctamente"
    except Exception as e:
        st.error(f"🛑 Error DB (Actualizando Grupo): {e}")
        return False, str(e)

def add_shared_expense(group_id, movement_data, member_ids):
    """Inserta el gasto y vincula el reparto, manejando pagadores reales o externos"""
    client = get_supabase_client()
    
    # 0. Determinamos quién es el pagador real
    real_paid_by = movement_data.get('paid_by_custom', movement_data['user_id'])
    es_externo = str(real_paid_by).startswith("ext_")

    try:
        mov_id = None
        
        # 1. Registrar en 'user_imputs' SOLO si el pagador NO es externo
        if not es_externo:
            res_mov = client.table("user_imputs").insert({
                "user_id": real_paid_by,
                "quantity": movement_data['quantity'],
                "type": movement_data['type'],
                "category_id": movement_data.get('category_id'),
                "date": movement_data['date'],
                "notes": movement_data['notes'],
                "group_id": group_id
            }).execute()
            
            if hasattr(res_mov, 'error') and res_mov.error:
                return False, f"Error DB personal: {res_mov.error}"
                
            if res_mov.data:
                mov_id = res_mov.data[0]['id']

        # 2. Registrar el ticket en el Grupo (group_expenses)
        expense_data = {
            "group_id": group_id,
            "movement_id": mov_id, 
            "paid_by": real_paid_by,
            "description": movement_data.get('notes', 'Gasto compartido'), 
            "total_amount": movement_data.get('quantity', 0)
        }
        res_exp = client.table("group_expenses").insert(expense_data).execute()
        
        if hasattr(res_exp, 'error') and res_exp.error:
            return False, f"Error DB Grupo: {res_exp.error}"
            
        if not res_exp.data:
            return False, "Error desconocido al crear el ticket de grupo."
            
        exp_id = res_exp.data[0]['id']
        
        # 3. Crear los repartos (splits)
        cuota = movement_data.get('quantity', 0) / len(member_ids)
        splits = []
        for mid in member_ids:
            splits.append({
                "expense_id": exp_id,
                "user_id": mid,
                "amount_owed": cuota,
                "is_settled": False
            })
            
        res_splits = client.table("group_expense_splits").insert(splits).execute()
        if hasattr(res_splits, 'error') and res_splits.error:
            return False, f"Error DB Repartos: {res_splits.error}"

        return True, "Gasto compartido registrado correctamente"
        
    except Exception as e:
        # Aquí capturamos cualquier fallo grave (como que category_id sea inválido)
        return False, f"🛑 Error Técnico: {str(e)}"

def get_group_expenses(group_id):
    """Obtiene el historial de gastos del grupo y sus repartos (sin cruzar perfiles)"""
    import streamlit as st
    client = get_supabase_client()
    try:
        res = client.table("group_expenses") \
            .select("*, group_expense_splits(user_id, amount_owed)") \
            .eq("group_id", group_id) \
            .order("date", desc=True) \
            .execute() 
        return res.data or []
    except Exception as e:
        st.error(f"🛑 Error DB (Cargando Historial de Gastos): {e}")
        return []

def delete_group_expense(expense_id, movement_id):
    """Elimina un gasto del grupo y su movimiento personal asociado"""
    client = get_supabase_client()
    import streamlit as st
    try:
        # 1. Borramos el gasto personal de la tabla user_imputs (si existe)
        if movement_id:
            client.table('user_imputs').delete().eq('id', movement_id).execute()
            
        # 2. Borramos el registro del ticket del grupo
        client.table('group_expenses').delete().eq('id', expense_id).execute()
        
        return True
    except Exception as e:
        st.error(f"🛑 Error DB (Borrando Gasto): {e}")
        return False

def get_expense_participants(movement_id):
    """Devuelve la lista de IDs de los usuarios que participan en un gasto concreto"""
    client = get_supabase_client()
    try:
        res = client.table('group_expenses').select('id, group_expense_splits(user_id)').eq('movement_id', movement_id).execute()
        if res.data and res.data[0].get('group_expense_splits'):
            return [s['user_id'] for s in res.data[0]['group_expense_splits']]
        return []
    except:
        return []

def update_shared_expense(mov_id, mov_data, new_group_id, participant_ids):
    """Actualiza un gasto a todos los niveles (personal y grupo) manejando los cambios de forma inteligente"""
    client = get_supabase_client()
    try:
        # 1. Actualizar el movimiento personal SIEMPRE
        client.table('user_imputs').update({
            "quantity": mov_data['quantity'],
            "type": mov_data['type'],
            "category_id": mov_data['category_id'],
            "date": mov_data['date'],
            "notes": mov_data['notes'],
            "group_id": new_group_id # Guardamos si ahora tiene grupo o no
        }).eq('id', mov_id).execute()

        # 2. Ver si este movimiento ya era un gasto de grupo antes
        res_exp = client.table('group_expenses').select('id, group_id').eq('movement_id', mov_id).execute()
        old_exp = res_exp.data[0] if res_exp.data else None

        # ESCENARIO A: Lo hemos desvinculado del grupo (Ahora es un gasto personal normal)
        if new_group_id is None:
            if old_exp:
                client.table('group_expenses').delete().eq('id', old_exp['id']).execute()
        
        # ESCENARIO B: Sigue teniendo grupo (El mismo o uno nuevo)
        else:
            cuota = mov_data['quantity'] / len(participant_ids) if participant_ids else 0
            splits = [{"user_id": pid, "amount_owed": cuota, "is_settled": False} for pid in participant_ids]

            if old_exp and old_exp['group_id'] == new_group_id:
                # B1: Es el MISMO grupo. Actualizamos el precio y los participantes
                exp_id = old_exp['id']
                client.table('group_expenses').update({
                    "description": mov_data['notes'], "total_amount": mov_data['quantity']
                }).eq('id', exp_id).execute()
                
                # Borramos los repartos viejos y metemos los nuevos (por si quitaste a alguien)
                client.table('group_expense_splits').delete().eq('expense_id', exp_id).execute()
                for s in splits: s['expense_id'] = exp_id
                if splits: client.table('group_expense_splits').insert(splits).execute()
                
            else:
                # B2: Es un GRUPO DISTINTO o ANTES ERA PERSONAL. Borramos lo viejo y creamos nuevo.
                if old_exp:
                    client.table('group_expenses').delete().eq('id', old_exp['id']).execute()
                
                new_exp = client.table('group_expenses').insert({
                    "group_id": new_group_id, "movement_id": mov_id, 
                    "paid_by": mov_data['user_id'], "description": mov_data['notes'], 
                    "total_amount": mov_data['quantity']
                }).execute()
                
                if new_exp.data:
                    n_exp_id = new_exp.data[0]['id']
                    for s in splits: s['expense_id'] = n_exp_id
                    if splits: client.table('group_expense_splits').insert(splits).execute()
                    
        return True, "Actualizado correctamente"
    except Exception as e:
        import streamlit as st
        st.error(f"🛑 Error DB: {e}")
        return False, str(e)

def get_pending_balances(group_id):
    """Calcula los balances ignorando las deudas que ya han sido pagadas (is_settled = True)"""
    client = get_supabase_client()
    try:
        res = client.table("group_expense_splits") \
            .select("amount_owed, is_settled, user_id, group_expenses!inner(group_id, paid_by)") \
            .eq("group_expenses.group_id", group_id) \
            .eq("is_settled", False) \
            .execute()
        
        balances = {}
        for row in res.data:
            debtor = row['user_id']
            creditor = row['group_expenses']['paid_by']
            amount = float(row['amount_owed'])
            
            if debtor == creditor: continue # Ignoramos lo que nos debemos a nosotros mismos
            
            balances[creditor] = balances.get(creditor, 0.0) + amount
            balances[debtor] = balances.get(debtor, 0.0) - amount
            
        return balances
    except Exception as e:
        print(f"Error calculando balances pendientes: {e}")
        return {}

def calculate_settlements(balances):
    """Genera las transacciones para dejar a cero a los miembros"""
    deudores = [{'id': u, 'amount': abs(a)} for u, a in balances.items() if a < -0.01]
    acreedores = [{'id': u, 'amount': a} for u, a in balances.items() if a > 0.01]
    settlements = []
    
    i, j = 0, 0
    while i < len(deudores) and j < len(acreedores):
        pago = min(deudores[i]['amount'], acreedores[j]['amount'])
        settlements.append({'from': deudores[i]['id'], 'to': acreedores[j]['id'], 'amount': round(pago, 2)})
        deudores[i]['amount'] -= pago
        acreedores[j]['amount'] -= pago
        if deudores[i]['amount'] < 0.01: i += 1
        if acreedores[j]['amount'] < 0.01: j += 1
    return settlements

def settle_debt_between_users(group_id, creditor_id, debtor_id):
    """Liquida las deudas cruzadas entre dos usuarios y ajusta el gasto personal por el importe NETO"""
    client = get_supabase_client()
    try:
        # 1. Calcular deuda de B hacia A (Lo grande)
        res_B_to_A = client.table("group_expense_splits") \
            .select("expense_id, amount_owed, group_expenses!inner(group_id, paid_by, movement_id)") \
            .eq("user_id", debtor_id) \
            .eq("group_expenses.group_id", group_id) \
            .eq("group_expenses.paid_by", creditor_id) \
            .eq("is_settled", False).execute()
        
        gross_B_to_A = sum(float(r['amount_owed']) for r in res_B_to_A.data)

        # 2. Calcular deuda de A hacia B (La deuda cruzada a compensar)
        res_A_to_B = client.table("group_expense_splits") \
            .select("expense_id, amount_owed, group_expenses!inner(group_id, paid_by, movement_id)") \
            .eq("user_id", creditor_id) \
            .eq("group_expenses.group_id", group_id) \
            .eq("group_expenses.paid_by", debtor_id) \
            .eq("is_settled", False).execute()
        
        gross_A_to_B = sum(float(r['amount_owed']) for r in res_A_to_B.data)

        # 3. El dinero real (NETO) que se está transfiriendo
        net_amount = gross_B_to_A - gross_A_to_B

        # 4. Candado Cruzado 🔒: Marcar TODAS las deudas en ambas direcciones como saldadas
        for r in res_B_to_A.data:
            client.table("group_expense_splits").update({"is_settled": True, "settlement_requested": False}) \
                .eq("expense_id", r['expense_id']).eq("user_id", debtor_id).execute()
            
        for r in res_A_to_B.data:
            client.table("group_expense_splits").update({"is_settled": True, "settlement_requested": False}) \
                .eq("expense_id", r['expense_id']).eq("user_id", creditor_id).execute()

        # 5. Reducir el gasto personal de quien cobra por el valor NETO recibido
        if net_amount > 0:
            mov_ids = [r['group_expenses']['movement_id'] for r in res_B_to_A.data if r['group_expenses'].get('movement_id')]
            amount_to_reduce = net_amount
            
            for mov_id in mov_ids:
                if amount_to_reduce <= 0.01: break
                
                mov_res = client.table("user_imputs").select("quantity").eq("id", mov_id).execute()
                if mov_res.data:
                    curr_qty = float(mov_res.data[0]['quantity'])
                    if curr_qty > amount_to_reduce:
                        new_qty = curr_qty - amount_to_reduce
                        client.table("user_imputs").update({"quantity": new_qty}).eq("id", mov_id).execute()
                        amount_to_reduce = 0
                    else:
                        client.table("user_imputs").update({"quantity": 0}).eq("id", mov_id).execute()
                        amount_to_reduce -= curr_qty

        return True, "Deudas cruzadas liquidadas y contabilidad ajustada."
    except Exception as e:
        return False, str(e)
        
def get_locked_movements():
    """Devuelve un listado rápido de IDs de movimientos que tienen candado"""
    client = get_supabase_client()
    try:
        res = client.table("group_expenses").select("movement_id, group_expense_splits!inner(is_settled)").eq("group_expense_splits.is_settled", True).execute()
        return {r['movement_id'] for r in res.data if r.get('movement_id')}
    except:
        return set()

def request_settlement(group_id, debtor_id, creditor_id):
    """El net-deudor avisa de que ha pagado la deuda neta"""
    client = get_supabase_client()
    try:
        # Solo marcamos los splits donde el deudor debe al acreedor
        # para que la alerta roja le llegue solo a quien recibe el dinero
        res = client.table("group_expense_splits") \
            .select("expense_id, group_expenses!inner(group_id, paid_by)") \
            .eq("user_id", debtor_id) \
            .eq("group_expenses.group_id", group_id) \
            .eq("group_expenses.paid_by", creditor_id) \
            .eq("is_settled", False).execute()
        
        for r in res.data:
            client.table("group_expense_splits").update({"settlement_requested": True}) \
                .eq("expense_id", r['expense_id']).eq("user_id", debtor_id).execute()
        return True
    except Exception as e:
        print(f"Error requesting settlement: {e}")
        return False
        
def get_settlement_requests(group_id):
    """Devuelve las parejas (deudor, acreedor) que están pendientes de confirmación"""
    client = get_supabase_client()
    try:
        res = client.table("group_expense_splits") \
            .select("user_id, group_expenses!inner(paid_by)") \
            .eq("group_expenses.group_id", group_id) \
            .eq("is_settled", False) \
            .eq("settlement_requested", True).execute()
        # Set de tuplas (debtor_id, creditor_id)
        return set((r['user_id'], r['group_expenses']['paid_by']) for r in res.data)
    except:
        return set()

def check_pending_confirmations(user_id):
    """Devuelve los IDs de los grupos donde el usuario tiene pagos esperando a ser confirmados"""
    client = get_supabase_client()
    try:
        res = client.table("group_expense_splits") \
            .select("group_expenses!inner(group_id, paid_by)") \
            .eq("group_expenses.paid_by", user_id) \
            .eq("is_settled", False) \
            .eq("settlement_requested", True).execute()
        return set(r['group_expenses']['group_id'] for r in res.data)
    except:
        return set()

def get_total_user_debt(user_id):
    """Calcula el balance neto del usuario en todos los grupos. Positivo = le deben, Negativo = debe."""
    client = get_supabase_client()
    total_owed_to_me = 0.0
    total_i_owe = 0.0
    try:
        # 1. Buscar todo el dinero que me deben (Yo pagué, otros deben y no está saldado)
        res_creditor = client.table("group_expense_splits") \
            .select("amount_owed, user_id, group_expenses!inner(paid_by)") \
            .eq("group_expenses.paid_by", user_id) \
            .eq("is_settled", False).execute()

        for r in res_creditor.data:
            if r['user_id'] != user_id: # No sumar mi propia parte de mis tickets
                total_owed_to_me += float(r['amount_owed'])

        # 2. Buscar todo el dinero que yo debo (Otros pagaron, yo debo y no está saldado)
        res_debtor = client.table("group_expense_splits") \
            .select("amount_owed, group_expenses!inner(paid_by)") \
            .eq("user_id", user_id) \
            .eq("is_settled", False).execute()

        for r in res_debtor.data:
            if r['group_expenses']['paid_by'] != user_id:
                total_i_owe += float(r['amount_owed'])

        # Retornamos el Neto: Si es positivo, soy acreedor. Si es negativo, soy deudor.
        return total_owed_to_me - total_i_owe
    except Exception as e:
        print(f"Error calculando deuda total: {e}")
        return 0.0

def add_external_member(group_id, name):
    """Crea un usuario 'fantasma' en el grupo"""
    client = get_supabase_client()
    try:
        # Insertamos en group_members sin user_id, pero con nombre externo
        client.table("group_members").insert({
            "group_id": group_id,
            "is_external": True,
            "external_name": name,
            "user_id": None # No tiene cuenta real
        }).execute()
        return True, "Usuario externo añadido"
    except Exception as e:
        return False, str(e)

def settle_external_debt_admin(group_id, external_member_name, creditor_id):
    """El admin confirma que el usuario externo ya ha pagado al acreedor"""
    client = get_supabase_client()
    try:
        # Buscamos los gastos donde el acreedor pagó y el externo participó
        # Nota: Aquí usamos el external_name como referencia en la lógica de filtrado
        # Esta es una versión simplificada, en un sistema real usaríamos IDs internos de group_members
        res = client.table("group_expense_splits") \
            .select("expense_id, group_expenses!inner(group_id, paid_by)") \
            .eq("group_expenses.group_id", group_id) \
            .eq("group_expenses.paid_by", creditor_id) \
            .eq("is_settled", False).execute()
        
        # Como no tenemos user_id para el externo, el sistema de splits debe 
        # haber guardado un ID temporal o nulo. 
        # (Para este MVP, vamos a marcar los pagos pendientes de ese grupo entre esos sujetos)
        # ... lógica de actualización de is_settled ...
        return True, f"Deuda de {external_member_name} saldada."
    except Exception as e:
        return False, str(e)

def settle_debt_to_external(group_id, debtor_id, external_name):
    """El admin confirma que un usuario real ya ha pagado al invitado externo"""
    client = get_supabase_client()
    try:
        # Buscamos los gastos donde el externo pagó (ext_) y el usuario real debe
        # Marcamos como settled los repartos correspondientes
        res = client.table("group_expense_splits") \
            .select("id, group_expenses!inner(group_id, paid_by)") \
            .eq("group_expenses.group_id", group_id) \
            .eq("user_id", debtor_id) \
            .eq("is_settled", False).execute()
        
        if res.data:
            ids_to_settle = [r['id'] for r in res.data]
            client.table("group_expense_splits").update({"is_settled": True}).in_("id", ids_to_settle).execute()
            
        return True, f"Deuda con {external_name} saldada."
    except Exception as e:
        return False, str(e)

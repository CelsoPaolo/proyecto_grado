<script setup>
/* CU-CAT-02 y CU-CAT-03 (RF-09, RF-10, RF-14).

   Los errores de validacion llegan del servidor asociados a su campo y
   se muestran junto a el (RNF-15). La interfaz no reimplementa las
   reglas: el precio y las existencias se validan en el servidor, que
   es donde viven RN-CAT-01 y RN-CAT-02.

   Las existencias solo se fijan al CREAR el producto (RN-CAT-10). Al
   editar se muestran sin poder cambiarlas y no se envian: el servidor
   rechaza con 400 una edicion que las incluya, porque desde la v1.4
   solo cambian por venta, anulacion o ajuste con motivo, que dejan su
   movimiento. Se corrigen con «Ajustar existencias», en el detalle del
   producto (AjustarExistencias.vue). */
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import { useToast } from 'primevue/usetoast'
import { computed, ref, watch } from 'vue'

import { productosApi } from '@/api/catalogo'
import { useErroresApi } from '@/composables/useErroresApi'

const props = defineProps({
  visible: { type: Boolean, default: false },
  producto: { type: Object, default: null },
  categorias: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:visible', 'guardado'])

const toast = useToast()
const { mensajeGeneral, registrar, limpiar, errorDe } = useErroresApi()

const VACIO = {
  nombre: '',
  descripcion: '',
  precio: null,
  stock: 0,
  categoria: null,
  codigo_fabrica: '',
  meses_garantia: 0,
  imagen: null,
}

const formulario = ref({ ...VACIO })
const guardando = ref(false)
const vistaPrevia = ref(null)

const editando = computed(() => Boolean(props.producto))
const titulo = computed(() => (editando.value ? 'Editar producto' : 'Nuevo producto'))

watch(
  () => props.visible,
  (abierto) => {
    if (!abierto) return
    limpiar()
    vistaPrevia.value = props.producto?.imagen ?? null
    formulario.value = props.producto
      ? {
          nombre: props.producto.nombre,
          descripcion: props.producto.descripcion ?? '',
          precio: Number(props.producto.precio),
          stock: props.producto.stock,
          categoria: props.producto.categoria,
          codigo_fabrica: props.producto.codigo_fabrica ?? '',
          meses_garantia: props.producto.meses_garantia ?? 0,
          imagen: null,
        }
      : { ...VACIO }
  },
)

function alElegirImagen(evento) {
  const archivo = evento.target.files?.[0] ?? null
  formulario.value.imagen = archivo
  vistaPrevia.value = archivo ? URL.createObjectURL(archivo) : null
}

function cerrar() {
  emit('update:visible', false)
}

async function guardar() {
  limpiar()
  guardando.value = true
  try {
    const datos = { ...formulario.value }
    if (!datos.imagen) delete datos.imagen

    if (editando.value) {
      // RN-CAT-10: enviarlas, aunque no hayan cambiado, haria que el
      // servidor rechazara la edicion entera.
      delete datos.stock
      await productosApi.actualizar(props.producto.id, datos)
      toast.add({ severity: 'success', summary: 'Producto actualizado', life: 3000 })
    } else {
      await productosApi.crear(datos)
      toast.add({ severity: 'success', summary: 'Producto registrado', life: 3000 })
    }
    emit('guardado')
  } catch (error) {
    registrar(error)
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <Dialog
    :visible="visible"
    :header="titulo"
    modal
    :style="{ width: '34rem' }"
    @update:visible="emit('update:visible', $event)"
  >
    <form class="formulario" @submit.prevent="guardar">
      <div class="campo">
        <label for="nombre">Nombre</label>
        <InputText
          id="nombre"
          v-model="formulario.nombre"
          :invalid="Boolean(errorDe('nombre'))"
        />
        <small v-if="errorDe('nombre')" class="error">{{ errorDe('nombre') }}</small>
      </div>

      <div class="campo">
        <label for="categoria">Categoría</label>
        <Select
          id="categoria"
          v-model="formulario.categoria"
          :options="categorias"
          option-label="nombre"
          option-value="id"
          placeholder="Seleccione una categoría"
          :invalid="Boolean(errorDe('categoria'))"
        />
        <small v-if="errorDe('categoria')" class="error">
          {{ errorDe('categoria') }}
        </small>
        <small v-if="categorias.length === 0" class="ayuda">
          Debe crear al menos una categoría antes de registrar productos.
        </small>
      </div>

      <div class="fila">
        <div class="campo">
          <label for="precio">Precio (Bs)</label>
          <InputNumber
            input-id="precio"
            v-model="formulario.precio"
            mode="decimal"
            :min-fraction-digits="2"
            :max-fraction-digits="2"
            :invalid="Boolean(errorDe('precio'))"
          />
          <small v-if="errorDe('precio')" class="error">{{ errorDe('precio') }}</small>
        </div>

        <div class="campo">
          <label for="stock">Existencias</label>
          <InputNumber
            input-id="stock"
            v-model="formulario.stock"
            :min="0"
            :show-buttons="!editando"
            :disabled="editando"
            :invalid="Boolean(errorDe('stock'))"
          />
          <small v-if="errorDe('stock')" class="error">{{ errorDe('stock') }}</small>
          <small v-else-if="editando" class="ayuda">
            No se editan aquí: se corrigen con un ajuste de inventario, que
            exige un motivo.
          </small>
        </div>
      </div>

      <!-- RF-72. Cambiarlo solo afecta a las ventas futuras: cada venta
           guarda su propia copia (RN-VEN-12). -->
      <div class="campo">
        <label for="meses_garantia">Garantía (meses)</label>
        <InputNumber
          input-id="meses_garantia"
          v-model="formulario.meses_garantia"
          :min="0"
          show-buttons
          :invalid="Boolean(errorDe('meses_garantia'))"
        />
        <small v-if="errorDe('meses_garantia')" class="error">
          {{ errorDe('meses_garantia') }}
        </small>
        <small v-else class="ayuda">
          0 = sin garantía. Si lo cambia, las ventas ya registradas conservan la
          garantía con la que se vendieron.
        </small>
      </div>

      <div class="campo">
        <label for="descripcion">Descripción</label>
        <Textarea id="descripcion" v-model="formulario.descripcion" rows="3" />
      </div>

      <!-- RF-97: el código que trae impreso el producto o su caja. El
           código interno no aparece aquí: lo asigna el sistema y no se
           edita (RN-CAT-08). -->
      <div class="campo">
        <label for="codigo_fabrica">
          Código de fábrica <span class="ayuda">(opcional)</span>
        </label>
        <InputText
          id="codigo_fabrica"
          v-model="formulario.codigo_fabrica"
          maxlength="50"
          :invalid="Boolean(errorDe('codigo_fabrica'))"
        />
        <small v-if="errorDe('codigo_fabrica')" class="error">
          {{ errorDe('codigo_fabrica') }}
        </small>
        <small v-else class="ayuda">
          Si la caja trae código de barras, regístrelo para venderlo leyéndolo
          directamente. Déjelo vacío si no tiene.
        </small>
      </div>

      <div class="campo">
        <label for="imagen">Imagen <span class="ayuda">(opcional)</span></label>
        <input
          id="imagen"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          @change="alElegirImagen"
        />
        <img v-if="vistaPrevia" :src="vistaPrevia" alt="Vista previa" class="previa" />
        <small v-if="errorDe('imagen')" class="error">{{ errorDe('imagen') }}</small>
      </div>

      <Message v-if="mensajeGeneral" severity="error" :closable="false">
        {{ mensajeGeneral }}
      </Message>

      <div class="pie">
        <Button label="Cancelar" text @click="cerrar" />
        <Button type="submit" label="Guardar" icon="pi pi-check" :loading="guardando" />
      </div>
    </form>
  </Dialog>
</template>

<style scoped>
.formulario {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.fila {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

@media (max-width: 520px) {
  .fila {
    grid-template-columns: 1fr;
  }
}

.campo {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.campo label {
  font-weight: 600;
  font-size: 0.9rem;
}

.error {
  color: var(--p-red-500, #ef4444);
}

.ayuda {
  color: var(--p-text-muted-color, #71717a);
  font-weight: 400;
}

.previa {
  width: 96px;
  height: 96px;
  object-fit: cover;
  border-radius: 8px;
  margin-top: 0.25rem;
}

.pie {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>

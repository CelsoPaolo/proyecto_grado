<script setup>
/* Pantalla provisional de T-0.8: verifica que PrimeVue, el tema Aura y
   el locale en espanol estan correctamente montados, y que la
   disposicion se mantiene legible en ancho de tableta (RNF-12).
   El <RouterView> y el menu por rol llegan en T-1.10. */
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'

const bloques = [
  { nombre: 'Catálogo e inventario', icono: 'pi pi-box' },
  { nombre: 'Registro de ventas', icono: 'pi pi-shopping-cart' },
  { nombre: 'Servicios técnicos', icono: 'pi pi-wrench' },
  { nombre: 'Gestión de usuarios', icono: 'pi pi-users' },
  { nombre: 'Panel de indicadores', icono: 'pi pi-chart-bar' },
]
</script>

<template>
  <div class="pcs-contenedor">
    <header class="cabecera">
      <div>
        <h1>PC-Solution ERP</h1>
        <p class="subtitulo">Sistema interno · Sucre, Bolivia</p>
      </div>
      <Tag value="En construcción" severity="warn" />
    </header>

    <Card>
      <template #title>Andamiaje del frontend</template>
      <template #subtitle>
        Vue 3 · Vite · Pinia · PrimeVue 4 (tema Aura) · locale en español
      </template>
      <template #content>
        <ul class="modulos">
          <li v-for="bloque in bloques" :key="bloque.nombre">
            <i :class="bloque.icono" />
            <span>{{ bloque.nombre }}</span>
          </li>
        </ul>
      </template>
      <template #footer>
        <Button label="Componente de PrimeVue" icon="pi pi-check" />
      </template>
    </Card>
  </div>
</template>

<style scoped>
.cabecera {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}

h1 {
  margin: 0;
  font-size: 1.5rem;
}

.subtitulo {
  margin: 0.25rem 0 0;
  color: var(--p-text-muted-color, #64748b);
  font-size: 0.9rem;
}

/* Rejilla adaptable: se reacomoda sola sin scroll horizontal (RNF-12). */
.modulos {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.75rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.modulos li {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.75rem;
  border: 1px solid var(--p-surface-200, #e2e8f0);
  border-radius: var(--pcs-radio);
  background: var(--p-surface-0, #fff);
}
</style>

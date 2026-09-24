<script setup>
/* Destino del guard cuando un rol intenta entrar donde no le
   corresponde. Es usabilidad: el servidor ya habria respondido 403
   igualmente (RN-ACC-04). */
import Button from 'primevue/button'
import Card from 'primevue/card'
</script>

<template>
  <Card class="tarjeta">
    <template #title>Sin permiso</template>
    <template #content>
      <p>
        Su rol no tiene acceso a esa sección. Si cree que debería tenerlo,
        consulte con el administrador del sistema.
      </p>
    </template>
    <template #footer>
      <RouterLink :to="{ name: 'inicio' }">
        <Button label="Volver al inicio" icon="pi pi-home" />
      </RouterLink>
    </template>
  </Card>
</template>

<style scoped>
.tarjeta {
  max-width: 520px;
}
</style>

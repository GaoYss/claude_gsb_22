<template>
  <el-dialog :model-value="visible"
             :title="isEdit ? `编辑绿植更换记录 · ${form.replacement_no}` : '登记绿植更换记录'"
             width="760px" top="6vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
      <el-form-item label="所属绿地" prop="green_space_id" :error="fieldErrors.green_space_id">
        <GreenSpaceSelect v-model="form.green_space_id" :preset="spacePreset"
                          @update:model-value="onGreenSpaceChange" />
      </el-form-item>
      <el-form-item label="关联养护记录" :error="fieldErrors.maintenance_record_id">
        <RecordSelect v-model="form.maintenance_record_id" :green-space-id="form.green_space_id"
                      :preset="recordPreset" />
        <div class="form-hint">如本次更换源于某次养护作业（如补植、病虫害防治），可关联对应养护记录。</div>
      </el-form-item>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="植株名称" prop="plant_name" :error="fieldErrors.plant_name">
            <el-input v-model="form.plant_name" placeholder="如：香樟" maxlength="96" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="植物类别" prop="plant_category" :error="fieldErrors.plant_category">
            <el-select v-model="form.plant_category" placeholder="请选择" style="width: 100%">
              <el-option v-for="item in categoryOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="规格" :error="fieldErrors.spec">
            <el-input v-model="form.spec" placeholder="如：胸径 25-30cm" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="更换原因" prop="reason" :error="fieldErrors.reason">
            <el-select v-model="form.reason" placeholder="请选择" style="width: 100%">
              <el-option v-for="item in reasonOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="更换数量" prop="quantity" :error="fieldErrors.quantity">
            <el-input-number v-model="form.quantity" :min="0.01" :max="999999" :precision="2"
                             :controls="false" placeholder="请输入数量" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="计量单位" :error="fieldErrors.unit">
            <el-select v-model="form.unit" style="width: 100%">
              <el-option v-for="item in unitOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="苗木来源" prop="plant_source" :error="fieldErrors.plant_source">
            <el-select v-model="form.plant_source" clearable placeholder="请选择自产苗 / 外购苗"
                       style="width: 100%">
              <el-option v-for="item in sourceOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
            <div class="form-hint">自产苗登记自有苗圃与内部计价，外购苗登记供货单位与采购单价；不登记将在清单中标记。</div>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="原植株状况" :error="fieldErrors.old_plant_status">
            <el-select v-model="form.old_plant_status" clearable placeholder="请选择" style="width: 100%">
              <el-option v-for="item in oldStatusOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="更换日期" prop="replace_date" :error="fieldErrors.replace_date">
            <el-date-picker v-model="form.replace_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择日期" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="单价（元）" :error="fieldErrors.unit_price">
            <el-input-number v-model="form.unit_price" :min="0" :precision="2" :controls="false"
                             placeholder="留空则不计金额" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="金额（元）">
            <el-input :model-value="computedAmount" disabled />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="供苗单位" :error="fieldErrors.supplier">
            <el-input v-model="form.supplier" :placeholder="supplierPlaceholder" maxlength="96" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="登记人" :error="fieldErrors.operator">
            <el-input v-model="form.operator" maxlength="64" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="备注" :error="fieldErrors.remark">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="2000" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { plantReplacementApi } from '@/api'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import RecordSelect from '@/components/common/RecordSelect.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { formatCurrency, today } from '@/utils/format'

const emit = defineEmits(['saved'])

const { options: categoryOptions } = useEnumOptions('plant_category')
const { options: reasonOptions } = useEnumOptions('replacement_reason')
const { options: oldStatusOptions } = useEnumOptions('old_plant_status')
const { options: unitOptions } = useEnumOptions('measure_unit')
const { options: sourceOptions } = useEnumOptions('plant_source')

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const spacePreset = ref(null)
const recordPreset = ref(null)
const form = reactive(emptyForm())

const isEdit = computed(() => editingId.value !== null)

const supplierPlaceholder = computed(() => {
  if (form.plant_source === 'self_grown') return '自产苗供苗单位，如：中心自有苗圃'
  if (form.plant_source === 'purchased') return '外购苗供货单位，如：萧山苗木合作社'
  return '请先选择苗木来源'
})

const computedAmount = computed(() => {
  if (form.unit_price === null || form.unit_price === undefined || form.unit_price === '') return '填写单价后自动核算'
  const amount = Number(form.quantity || 0) * Number(form.unit_price || 0)
  return formatCurrency(Number.isFinite(amount) ? amount : 0)
})

const rules = {
  green_space_id: [{ required: true, message: '请选择所属绿地', trigger: 'change' }],
  plant_name: [{ required: true, message: '请输入植株名称', trigger: 'blur' }],
  plant_category: [{ required: true, message: '请选择植物类别', trigger: 'change' }],
  quantity: [{ required: true, message: '请输入更换数量', trigger: 'blur' }],
  reason: [{ required: true, message: '请选择更换原因', trigger: 'change' }],
  replace_date: [{ required: true, message: '请选择更换日期', trigger: 'change' }],
}

function emptyForm() {
  return {
    replacement_no: '',
    green_space_id: null,
    maintenance_record_id: null,
    plant_name: '',
    plant_category: 'tree',
    spec: '',
    quantity: null,
    unit: 'plant',
    reason: 'dead',
    old_plant_status: '',
    replace_date: today(),
    plant_source: '',
    supplier: '',
    unit_price: null,
    operator: '',
    remark: '',
  }
}

function open(row = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  spacePreset.value = null
  recordPreset.value = null
  editingId.value = row?.id ?? null
  if (row) {
    Object.keys(form).forEach((key) => {
      if (row[key] !== undefined && row[key] !== null) form[key] = row[key]
    })
    spacePreset.value = row.green_space || null
    recordPreset.value = row.record ? { ...row.record, id: row.maintenance_record_id } : null
  }
  visible.value = true
}

function close() {
  visible.value = false
}

function onGreenSpaceChange() {
  form.maintenance_record_id = null
  recordPreset.value = null
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  fieldErrors.value = {}
  const payload = { ...form }
  if (!payload.replacement_no) delete payload.replacement_no
  if (!payload.maintenance_record_id) payload.maintenance_record_id = null
  if (!payload.old_plant_status) payload.old_plant_status = null
  if (!payload.plant_source) payload.plant_source = null
  if (!payload.supplier) payload.supplier = null
  try {
    if (isEdit.value) {
      await plantReplacementApi.update(editingId.value, payload)
      ElMessage.success('绿植更换记录已更新')
    } else {
      await plantReplacementApi.create(payload)
      ElMessage.success('绿植更换记录登记成功')
    }
    emit('saved')
    close()
  } catch (error) {
    fieldErrors.value = error?.details || {}
  } finally {
    submitting.value = false
  }
}

defineExpose({ open })
</script>

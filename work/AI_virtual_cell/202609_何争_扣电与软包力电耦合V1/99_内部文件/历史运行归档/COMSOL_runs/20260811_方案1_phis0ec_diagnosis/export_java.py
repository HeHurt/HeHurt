from com.comsol.model.util import ModelUtil

source = r"C:\HithiumSSD\hithium\work\MIC_LDS\202608_何争_不同集流体导出方式对电芯性能的影响\方案1.mph"
output = r"C:\HithiumSSD\hithium\COMSOL\runs\20260811_方案1_phis0ec_diagnosis\方案1_export.java"
tag = "plan1_export"

try:
    ModelUtil.remove(tag)
except Exception:
    pass

model = ModelUtil.load(tag, source)
try:
    model.save(output)
    print(output)
finally:
    ModelUtil.remove(tag)

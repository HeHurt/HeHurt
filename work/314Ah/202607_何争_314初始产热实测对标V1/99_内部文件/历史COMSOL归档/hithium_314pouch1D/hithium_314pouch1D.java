/*
 * hithium_314pouch1D.java
 */

import com.comsol.model.*;
import com.comsol.model.util.*;

/** Model exported on May 21 2026, 11:18 by COMSOL 6.4.0.293. */
public class hithium_314pouch1D {

  public static Model run() {
    Model model = ModelUtil.create("Model");

    model.modelPath("d:\\Users\\hez\\Desktop\\hithium\\COMSOL");

    model.label("hithium_314pouch1D.mph");

    model.param().set("rp_pos", "0.86[um]/2", "from 320D50");
    model.param().set("rp_neg", "11.80[um]/2", "from 320D50");
    model.param().set("epsl_neg", "1-epss_neg/content_pos", "314");
    model.param().set("cl_0", "900[mol/m^3]", "320");
    model.param().set("T", "25[degC]");
    model.param().set("L_pos", "84[um]", "pos 183um \u94dd\u7b9413");
    model.param().set("L_neg", "61.5[um]", "neg 320");
    model.param().set("L_sep", "12.8[um]", "320");
    model.param().set("L_negCC", "8[um]", "320");
    model.param().set("L_posCC", "14[um]", "320");
    model.param().set("epss_pos", "den_pos/(rho_pos*L_pos)*content_pos", "pos 314");
    model.param().set("epsl_sep", "0.38", "314");
    model.param().set("epsl_pos", "1-epss_pos/content_pos", "314");
    model.param().set("epss_neg", "den_neg/(rho_neg*L_neg)*content_neg", "314");
    model.param().set("L_JR_pos", "682[mm]");
    model.param().set("W_JR_pos", "86[mm]", "320");
    model.param().set("q_batt_pos", "cap_pos*den_pos*Ac", "pos");
    model.param().set("Ac", "L_JR_pos*W_JR_pos*2", "\u53e0\u7247");
    model.param().set("cap_pos", "144[mAh/g]", "pos");
    model.param().set("den_pos", "0.2143[mg/mm^2]", "CW320");
    model.param().set("den_pos_I", "cap_pos*den_pos/1[h]*Ac");
    model.param().set("i_1C", "den_pos_I", "320");
    model.param().set("C", "0.5");
    model.param().set("ah_pos", "q_batt_pos/3600[s]", "pos");
    model.param().set("L_JR_neg", "682[mm]");
    model.param().set("W_JR_neg", "86[mm]", "320");
    model.param().set("q_batt_neg", "cap_neg*den_neg*Ac");
    model.param().set("Ac_neg", "L_JR_neg*W_JR_neg*2", "\u53e0\u7247");
    model.param().set("cap_neg", "352.8[mAh/g]");
    model.param().set("den_neg", "0.0983[mg/mm^2]", "CW320");
    model.param().set("ah_neg", "q_batt_neg/3600[s]");
    model.param().set("sigma_pos", "0.04453[S/cm]", "320");
    model.param().set("sigma_neg", "100[S/m]", "pos");
    model.param().set("c0_pos", "csmax_pos*socini_pos");
    model.param().set("c0_neg", "csmax_neg*socini_neg");
    model.param().set("rho_neg", "2.2279[g/cm^3]", "\u771f\u5bc6\u5ea6320");
    model.param().set("rho_pos", "3.488[g/cm^3]", "\u771f\u5bc6\u5ea6320");
    model.param().set("csmax_pos", "rho_pos*cap_pos/F_const");
    model.param().set("csmax_neg", "rho_neg*cap_neg/F_const");
    model.param().set("cap_pos_extend", "cap_pos/(socmax_pos-socmin_pos)");
    model.param().set("cap_neg_extend", "cap_neg/(socmax_neg-socmin_neg)");
    model.param().set("content_pos", "0.981");
    model.param().set("content_neg", "0.973");
    model.param().group().create("par3");
    model.param("par3").set("socmin_pos", "0.0093164");
    model.param("par3").set("socmin_neg", "0.013641");
    model.param("par3").set("socmax_pos", "0.948");
    model.param("par3").set("socmax_neg", "0.84936");
    model.param("par3").set("ah_pos1", "ah_pos");
    model.param("par3").set("ah_neg1", "ah_neg");
    model.param("par3").set("ah_pos_soc1", "ah_pos*(socmax_pos-socmin_pos)");
    model.param("par3").set("ah_neg_soc1", "ah_neg*(socmax_neg-socmin_neg)");
    model.param("par3").set("Apos", "csmax_pos*epss_pos*L_pos*Ac*F_const/3600[s]*soc_pos");
    model.param("par3").set("Aneg", "csmax_neg*epss_neg*L_neg*Ac*F_const/3600[s]*soc_neg");
    model.param("par3").set("soc_pos", "(socmax_pos-socmin_pos)");
    model.param("par3").set("soc_neg", "(socmax_neg-socmin_neg)");
    model.param("par3").set("socini_neg", "0.013641+soc_neg*SOC");
    model.param("par3").set("socini_pos", "0.948-soc_pos*SOC");
    model.param("par3").set("SOC", "0");
    model.param().group().create("par2");
    model.param("par2").set("Es.Dneg", "60000[J/mol]");
    model.param("par2").set("Es.Dpos", "65000[J/mol]");
    model.param("par2").set("Es.kneg", "70000[J/mol]");
    model.param("par2").set("Es.kpos", "65000[J/mol]");
    model.param("par2").set("T_ref", "298.15[K]");
    model.param("par2").set("Sigma_pos", "4[S/m]", "\u6b63\u6781\u7535\u5bfc\u7387");
    model.param("par2").set("Sigma_neg", "4[S/m]", "\u8d1f\u6781\u7535\u5bfc\u7387");
    model.param("par2").set("k_pos", "1.1131E-10[m/s]/1.5");
    model.param("par2").set("Ds_pos", "1.6E-16 [m^2/s]/1.6");
    model.param("par2").set("Ds_neg", "1.060E-10[cm^2/s]");
    model.param("par2").set("Ds_neg_T", "Ds_neg*exp((Es.Dneg/R_const)*(1/(T_ref)-1/(T)))");
    model.param("par2").set("Ds_pos_T", "Ds_pos*exp((Es.Dpos/R_const)*(1/(T_ref)-1/(T)))");
    model.param("par2").set("k_pos_T", "k_pos*exp((Es.kpos/R_const)*(1/(T_ref)-1/(T)))");
    model.param("par2").set("k_neg_T", "k_neg*exp((Es.kneg/R_const)*(1/(T_ref)-1/(T)))");
    model.param("par2").set("k_neg", "1.2121E-9[m/s]");
    model.param("par3").label("OCV\u6821\u6b63");

    model.component().create("comp1", true);

    model.component("comp1").geom().create("geom1", 1);

    model.result().table().create("tbl10", "Table");
    model.result().table().create("tbl12", "Table");
    model.result().table().create("tbl13", "Table");
    model.result().table().create("tbl14", "Table");
    model.result().table().create("mrkvl1", "Table");
    model.result().table().create("tbl22", "Table");
    model.result().table().create("tbl31", "Table");
    model.result().table().create("tbl32", "Table");
    model.result().table().create("tbl33", "Table");
    model.result().table().create("tbl29", "Table");
    model.result().table().create("tbl30", "Table");
    model.result().table("tbl22").importData("25\u2103-C(CW391).dat");
    model.result().table("tbl31").importData("45\u2103-C(CW391).dat");
    model.result().table("tbl32").importData("25\u2103-G(CW511).dat");
    model.result().table("tbl33").importData("45\u2103-G(CW511).dat");

    model.component("comp1").func().create("step2", "Step");
    model.component("comp1").func().create("rect2", "Rectangle");
    model.component("comp1").func().create("gp1", "GaussianPulse");
    model.func().create("step1", "Step");
    model.component("comp1").func().create("int8", "Interpolation");
    model.component("comp1").func().create("int9", "Interpolation");
    model.component("comp1").func().create("int18", "Interpolation");
    model.component("comp1").func().create("int19", "Interpolation");
    model.component("comp1").func("step2").set("location", 10);
    model.component("comp1").func("step2").set("from", 6);
    model.component("comp1").func("step2").set("smooth", 20);
    model.component("comp1").func("rect2").label("\u5934\u90e8\u4fee\u6b63");
    model.component("comp1").func("rect2").set("lower", 0);
    model.component("comp1").func("rect2").set("upper", 0.15);
    model.component("comp1").func("rect2").set("amplitude", 0.03);
    model.component("comp1").func("rect2").set("smooth", 0.05);
    model.component("comp1").func("gp1").set("location", 0.01);
    model.component("comp1").func("gp1").set("sigma", 0.015);
    model.component("comp1").func("gp1").set("normalization", "peak");
    model.component("comp1").func("gp1").set("peakvalue", 0.05);
    model.func("step1").set("location", 1200);
    model.component("comp1").func("int8").label("\u8d1f\u6781K\u968fSOC\u53d8\u5316");
    model.component("comp1").func("int8")
         .set("table", new String[][]{{"0", "1"}, 
         {"0.1", "1"}, 
         {"0.2", "1"}, 
         {"0.3", "2"}, 
         {"0.4", "8"}, 
         {"0.5", "16"}, 
         {"0.6", "20"}, 
         {"0.65", "20"}, 
         {"0.7", "20"}, 
         {"0.8", "20"}, 
         {"0.9", "20"}, 
         {"1", "20"}});
    model.component("comp1").func("int8").set("interp", "piecewisecubic");
    model.component("comp1").func("int9").label("\u6b63\u6781K\u968fSOC\u53d8\u5316");
    model.component("comp1").func("int9")
         .set("table", new String[][]{{"0", "1"}, 
         {"0.1", "1"}, 
         {"0.15", "1"}, 
         {"0.2", "1"}, 
         {"0.3", "1"}, 
         {"0.4", "1"}, 
         {"0.5", "1"}, 
         {"0.6", "1"}, 
         {"0.7", "1"}, 
         {"0.8", "1"}, 
         {"0.9", "1"}, 
         {"1", "1"}});
    model.component("comp1").func("int18").label("\u8d1f\u6781D\u968fSOC\u53d8\u5316");
    model.component("comp1").func("int18")
         .set("table", new String[][]{{"0", "10"}, 
         {"0.1", "5.8"}, 
         {"0.2", "3"}, 
         {"0.3", "1.6"}, 
         {"0.4", "1"}, 
         {"0.5", "1"}, 
         {"0.6", "1"}, 
         {"0.65", "1"}, 
         {"0.7", "1"}, 
         {"0.8", "1"}, 
         {"0.9", "1"}, 
         {"1", "1"}});
    model.component("comp1").func("int18").set("interp", "piecewisecubic");
    model.component("comp1").func("int19").label("\u6b63\u6781D\u968fSOC\u53d8\u5316");
    model.component("comp1").func("int19")
         .set("table", new String[][]{{"0", "1"}, 
         {"0.1", "1"}, 
         {"0.2", "1"}, 
         {"0.3", "1"}, 
         {"0.4", "1"}, 
         {"0.5", "1"}, 
         {"0.6", "1"}, 
         {"0.65", "1"}, 
         {"0.7", "1"}, 
         {"0.8", "1"}, 
         {"0.9", "1"}, 
         {"1", "1"}});
    model.component("comp1").func("int19").set("interp", "piecewisecubic");

    model.component("comp1").mesh().create("mesh1");

    model.component("comp1").geom("geom1").create("i1", "Interval");
    model.component("comp1").geom("geom1").feature("i1").set("coordsource", "vector");
    model.component("comp1").geom("geom1").feature("i1")
         .set("coordvec", "0, L_negCC ,L_negCC+L_neg, L_negCC+L_neg+L_sep, L_negCC+L_neg+L_sep+L_pos,L_negCC+L_neg+L_sep+L_pos+L_posCC");
    model.component("comp1").geom("geom1").run();
    model.component("comp1").geom("geom1").run("fin");

    model.component("comp1").selection().create("sel1", "Explicit");
    model.component("comp1").selection("sel1").geom("geom1", 0);

    model.component("comp1").variable().create("var1");
    model.component("comp1").variable("var1").set("i_app", "i_1C*C");
    model.component("comp1").variable("var1").set("i_app_rest", "i_app*step1(18000-mod(t/1[s]-100,18100))");
    model.component("comp1").variable("var1").set("Q", "i_app*t");
    model.component("comp1").variable("var1").set("vol1", "vol");
    model.component("comp1").variable("var1")
         .set("I", "-3.5[A]*C*3.2[V]/(comp1.vol)*charge1+0[A]*charge2+3.5[A]*C*3.2[V]/(comp1.vol)*charge3");
    model.component("comp1").variable().create("var7");
    model.component("comp1").variable("var7")
         .set("EOCPneg_load", "if(liion.Its_ec1>0,mat1.elpot.Eeq_int5(liion.soc_surface_pce1),mat1.elpot.Eeq_int7(liion.soc_surface_pce1))", "\u8d1f\u8f7d\u4e0b-\u5f00\u8def\u7535\u4f4d\uff08\u57fa\u4e8e\u8868\u9762\u6d53\u5ea6\uff09");
    model.component("comp1").variable("var7")
         .set("EOCPneg", "if(liion.Its_ec1>0,mat1.elpot.Eeq_int5(liion.soc_average_pce1),mat1.elpot.Eeq_int7(liion.soc_average_pce1))", "\u5f00\u8def\u7535\u4f4d\uff08\u57fa\u4e8e\u5e73\u5747\u6d53\u5ea6\uff09");
    model.component("comp1").variable("var7")
         .set("EOCPpos_load", "if(liion.Its_ec1>0,mat3.elpot.Eeq_int15(liion.soc_surface_pce2)+0.02,mat3.elpot.Eeq_int15(liion.soc_surface_pce2)-0.02)", "\u8d1f\u8f7d\u4e0b-\u5f00\u8def\u7535\u4f4d\uff08\u57fa\u4e8e\u8868\u9762\u6d53\u5ea6\uff09");
    model.component("comp1").variable("var7")
         .set("EOCPpos", "if(liion.Its_ec1>0,mat3.elpot.Eeq_int15(liion.soc_average_pce2)+0.02,mat3.elpot.Eeq_int15(liion.soc_average_pce2)-0.02)", "\u5f00\u8def\u7535\u4f4d\uff08\u57fa\u4e8e\u5e73\u5747\u6d53\u5ea6\uff09");
    model.component("comp1").variable("var7")
         .set("EOCPall", "EOCPpos-EOCPneg", "\u5168\u7535\u6c60\u5f00\u8def\u7535\u4f4d\uff08\u57fa\u4e8e\u5e73\u5747\u6d53\u5ea6\uff09");
    model.component("comp1").variable("var7")
         .set("EOCPall_load", "EOCPpos_load-EOCPneg_load", "\u8d1f\u8f7d\u5168\u7535\u6c60\u5f00\u8def\u7535\u4f4d\uff08\u57fa\u4e8e\u8868\u9762\u6d53\u5ea6\uff09");
    model.component("comp1").variable("var7").set("i_app", "liion.Its_ec1");
    model.component("comp1").variable().create("var2");
    model.component("comp1").variable("var2")
         .set("dl_neg", "neg(( -(liion.Ilx*d(phil,x) ) - (liion.Ilx^2)/liion.sigmaleffxx )*1/abs(i_app/Ac))", "\u8d1f\u6781-\u6db2\u76f8\u6269\u6563\u6781\u5316");
    model.component("comp1").variable("var2")
         .set("dl_pos", "pos(( -(liion.Ilx*d(phil,x) ) - (liion.Ilx^2)/liion.sigmaleffxx )*1/abs(i_app/Ac))", "\u6b63\u6781-\u6db2\u76f8\u6269\u6563\u8fc7\u7535\u4f4d");
    model.component("comp1").variable("var2")
         .set("dl_sep", "sep(( -(liion.Ilx*d(phil,x) ) - (liion.Ilx^2)/liion.sigmaleffxx ) *1/abs(i_app/Ac))", "\u9694\u819c-\u6db2\u76f8\u6269\u6563\u8fc7\u7535\u4f4d");
    model.component("comp1").variable("var2")
         .set("ds_neg", "neg(liion.Av_pce1_per1*liion.iloc_per1*(EOCPneg_load-EOCPneg)*1/abs(i_app/Ac))", "\u8d1f\u6781-\u56fa\u76f8\u6d53\u5ea6\u6269\u6563\u8fc7\u7535\u4f4d");
    model.component("comp1").variable("var2")
         .set("ds_pos", "pos(liion.Av_pce2_per1*liion.iloc_per1*(EOCPpos_load-EOCPpos)*1/abs(i_app/Ac))", "\u6b63\u6781-\u56fa\u76f8\u6d53\u5ea6\u6269\u6563\u8fc7\u7535\u4f4d");
    model.component("comp1").variable("var2")
         .set("ohml_pos", "pos(liion.Ilx^2/liion.sigmaleffxx*1/abs(i_app/Ac))", "\u6b63\u6781-\u6db2\u76f8ohm\u6781\u5316");
    model.component("comp1").variable("var2")
         .set("ohms", "ohms_pos+ohms_neg+ohms_Cu+ohms_Al", "\u56fa\u76f8ohm\u6781\u5316");
    model.component("comp1").variable("var2")
         .set("RCT_neg", "neg(liion.Av_pce1_per1*liion.iloc_per1*(phis-phil-EOCPneg_load)*1/abs(i_app/Ac))", "\u8d1f\u6781-\u7535\u5316\u5b66\u53cd\u5e94\u8fc7\u7535\u4f4d");
    model.component("comp1").variable("var2")
         .set("ohms_neg", "neg(liion.Isx^2/liion.sigmaseffxx*1/abs(i_app/Ac))", "\u8d1f\u6781-\u56fa\u76f8ohm\u6781\u5316");
    model.component("comp1").variable("var2")
         .set("ohml_neg", "neg(liion.Ilx^2/liion.sigmaleffxx*1/abs(i_app/Ac))", "\u8d1f\u6781-\u6db2\u76f8ohm\u6781\u5316");
    model.component("comp1").variable("var2")
         .set("ohml_sep", "sep(liion.Ilx^2/liion.sigmaleffxx*1/abs(i_app/Ac))", "\u9694\u819c-\u6db2\u76f8ohm\u6781\u5316");
    model.component("comp1").variable("var2")
         .set("RCT_pos", "pos(liion.Av_pce2_per1*liion.iloc_per1*(phis-phil-EOCPpos_load)*1/abs(i_app/Ac))", "\u6b63\u6781-\u7535\u5316\u5b66\u53cd\u5e94\u8fc7\u7535\u4f4d");
    model.component("comp1").variable("var2")
         .set("total_pos", "dl_pos+ds_pos+ohml_pos+ohms_pos+RCT_pos", "\u6b63\u6781\u603b\u6781\u5316");
    model.component("comp1").variable("var2")
         .set("total_neg", "dl_neg+ds_neg+ohml_neg+ohms_neg+RCT_neg", "\u8d1f\u6781\u603b\u6781\u5316");
    model.component("comp1").variable("var2")
         .set("RCT", "RCT_neg+RCT_pos", "\u603b\u7535\u8377\u8f6c\u79fb\u6781\u5316");
    model.component("comp1").variable("var2").set("total_ohm", "ohml+ohms", "\u603bohm\u6781\u5316");
    model.component("comp1").variable("var2")
         .set("dl", "dl_neg+dl_sep+dl_pos", "\u6db2\u76f8\u6269\u6563\u6781\u5316");
    model.component("comp1").variable("var2").set("total", "total_neg+total_pos+total_sep");
    model.component("comp1").variable("var2").set("ds", "ds_neg+ds_pos", "\u56fa\u76f8\u6269\u6563\u6781\u5316");
    model.component("comp1").variable("var2").set("total_sep", "ohml_sep+dl_sep", "\u9694\u819c\u603b\u6781\u5316");
    model.component("comp1").variable("var2").set("polar", "liion.phis0_ec1-(EOCPpos-EOCPneg)");
    model.component("comp1").variable("var2")
         .set("ohml", "ohml_neg+ohml_sep+ohml_pos", "\u6db2\u76f8ohm\u6781\u5316");
    model.component("comp1").variable("var2")
         .set("ohms_pos", "pos(liion.Isx^2/liion.sigmaseffxx*1/abs(i_app/Ac))", "\u6b63\u6781-\u56fa\u76f8ohm\u6781\u5316");
    model.component("comp1").variable("var2")
         .set("ohms_Al", "poscc((liion.Isx^2+liion.Isy^2+liion.Isz^2)/liion.sigmaseffxx*1/abs(i_app/Ac))", "ohms_Al");
    model.component("comp1").variable("var2")
         .set("ohms_Cu", "negcc((liion.Isx^2+liion.Isy^2+liion.Isz^2)/liion.sigmaseffxx*1/abs(i_app/Ac))", "ohms_Cu");
    model.component("comp1").variable().create("var3");
    model.component("comp1").variable("var3").set("dl", "-2*R_const*T/cl/F_const*(1+liion.fcl)*(1-liion.tplus)*clx");
    model.component("comp1").variable("var3")
         .set("ds", "liion.Av_pce1_per1*liion.iloc_per1*(EOCPneg_load-EOCPneg)*1/(i_app/Ac)");
    model.component("comp1").variable("var3")
         .set("RCT", "liion.Av_pce1_per1*liion.iloc_per1*(phis-phil-EOCPneg_load)*1/(i_app/Ac)");
    model.component("comp1").variable("var3").set("ohml", "liion.Ilx^2/liion.sigmalxx*1/(i_app/Ac)");
    model.component("comp1").variable("var3").set("ohms", "liion.Isx^2/liion.sigmaxx*1/(i_app/Ac)");
    model.component("comp1").variable().create("var6");
    model.component("comp1").variable("var6")
         .set("L_all", "2*(L_pos+L_sep+L_neg)+L_negCC+L_posCC", "8\u5c42\u5355\u4f4d\u603b\u957f\u5ea6");
    model.component("comp1").variable("var6")
         .set("h_ave_all", "h_ave_negCC+h_ave_neg+h_ave_sep+h_ave_pos+h_ave_posCC", "\u603b\u4f53\u5e73\u5747\u4ea7\u70ed\u7387");
    model.component("comp1").variable("var6")
         .set("h_ave_negCC", "h_ohms_negCC", "negCC \u5e73\u5747\u4ea7\u70ed\u7387");
    model.component("comp1").variable("var6")
         .set("h_ohms_negCC", "avenegCC(-liion.isx*phisx)*L_negCC/L_all", "negCC \u56fa\u76f8ohm\u4ea7\u70ed\u7387");
    model.component("comp1").variable("var6")
         .set("h_ave_posCC", "h_ohms_posCC", "posCC \u5e73\u5747\u4ea7\u70ed\u7387");
    model.component("comp1").variable("var6")
         .set("h_ohms_posCC", "aveposCC(-liion.isx*phisx)*L_posCC/L_all", "posCC \u56fa\u76f8ohm\u4ea7\u70ed\u7387");
    model.component("comp1").variable("var6").set("h_ave_sep", "h_ohml_sep", "sep \u5e73\u5747\u4ea7\u70ed\u7387");
    model.component("comp1").variable("var6")
         .set("h_ohml_sep", "avesep(-liion.Ilx*philx)*L_sep*2/L_all", "sep \u6db2\u76f8ohm\u4ea7\u70ed\u7387");
    model.component("comp1").variable("var6")
         .set("h_ave_neg", "h_ohms_neg+h_ohml_neg+h_irre_neg+h_rev_neg", "neg \u5e73\u5747\u4ea7\u70ed\u7387");
    model.component("comp1").variable("var6")
         .set("h_ohms_neg", "aveneg(-liion.isx*phisx)*L_neg*2/L_all", "neg \u56fa\u76f8ohm\u4ea7\u70ed\u7387");
    model.component("comp1").variable("var6")
         .set("h_ohml_neg", "aveneg(-liion.Ilx*philx)*L_neg*2/L_all", "neg \u6db2\u76f8ohm\u4ea7\u70ed\u7387");
    model.component("comp1").variable("var6")
         .set("h_irre_neg", "aveneg(comp1.liion.Qirrevv_per1)*L_neg*2/L_all", "neg \u53cd\u5e94\u4e0d\u53ef\u9006\u70ed");
    model.component("comp1").variable("var6")
         .set("h_rev_neg", "aveneg(comp1.liion.Qrevv_per1)*L_neg*2/L_all", "neg \u53cd\u5e94\u53ef\u9006\u70ed");
    model.component("comp1").variable("var6")
         .set("h_ave_pos", "h_ohms_pos+h_ohml_pos+h_irre_pos+h_rev_pos", "pos \u5e73\u5747\u4ea7\u70ed\u7387");
    model.component("comp1").variable("var6")
         .set("h_ohms_pos", "avepos(-liion.isx*phisx)*L_pos*2/L_all", "pos \u56fa\u76f8ohm\u4ea7\u70ed\u7387");
    model.component("comp1").variable("var6")
         .set("h_ohml_pos", "avepos(-liion.Ilx*philx)*L_pos*2/L_all", "pos \u6db2\u76f8ohm\u4ea7\u70ed\u7387");
    model.component("comp1").variable("var6")
         .set("h_irre_pos", "avepos(comp1.liion.Qirrevv_per1)*L_pos*2/L_all", "pos \u53cd\u5e94\u4e0d\u53ef\u9006\u70ed");
    model.component("comp1").variable("var6")
         .set("h_rev_pos", "avepos(comp1.liion.Qrevv_per1)*L_pos*2/L_all", "pos \u53cd\u5e94\u53ef\u9006\u70ed");

    model.view().create("view4", 2);
    model.view().create("view5", 2);
    model.view().create("view6", 3);
    model.view().create("view7", 3);
    model.view().create("view10", 3);

    model.component("comp1").material().create("mat1", "Common");
    model.component("comp1").material().create("mat2", "Common");
    model.component("comp1").material().create("mat3", "Common");
    model.component("comp1").material().create("mat4", "Common");
    model.component("comp1").material().create("mat5", "Common");
    model.component("comp1").material("mat1").selection().set();
    model.component("comp1").material("mat1").propertyGroup("def").func().create("int1", "Interpolation");
    model.component("comp1").material("mat1").propertyGroup("def").func().create("int2", "Interpolation");
    model.component("comp1").material("mat1").propertyGroup()
         .create("ElectrodePotential", "ElectrodePotential", "Equilibrium potential");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func()
         .create("int1", "Interpolation");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func()
         .create("int2", "Interpolation");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func().create("an1", "Analytic");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func()
         .create("int3", "Interpolation");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func()
         .create("int4", "Interpolation");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func()
         .create("int5", "Interpolation");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func()
         .create("int6", "Interpolation");
    model.component("comp1").material("mat1").propertyGroup()
         .create("OperationalSOC", "OperationalSOC", "Operational electrode state-of-charge");
    model.component("comp1").material("mat1").propertyGroup().create("ic", "ic", "Intercalation strain");
    model.component("comp1").material("mat1").propertyGroup("ic").func().create("int1", "Interpolation");
    model.component("comp1").material("mat1").propertyGroup()
         .create("ElectrolyteConductivity", "ElectrolyteConductivity", "\u7535\u89e3\u8d28\u7535\u5bfc\u7387");
    model.component("comp1").material("mat1").selection().set(1, 2);
    model.component("comp1").material("mat2").selection().set(3);
    model.component("comp1").material("mat2").propertyGroup("def").func().create("int1", "Interpolation");
    model.component("comp1").material("mat2").propertyGroup()
         .create("ElectrolyteConductivity", "ElectrolyteConductivity", "Electrolyte conductivity");
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteConductivity").func()
         .create("int1", "Interpolation");
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteConductivity").func()
         .create("int2", "Interpolation");
    model.component("comp1").material("mat2").propertyGroup()
         .create("SpeciesProperties", "SpeciesProperties", "Species properties");
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties").func()
         .create("int1", "Interpolation");
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties").func()
         .create("int2", "Interpolation");
    model.component("comp1").material("mat2").propertyGroup()
         .create("ElectrolyteSaltConcentration", "ElectrolyteSaltConcentration", "Electrolyte salt concentration");
    model.component("comp1").material("mat3").selection().set(4);
    model.component("comp1").material("mat3").propertyGroup()
         .create("ElectrodePotential", "ElectrodePotential", "Equilibrium potential");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func()
         .create("int7", "Interpolation");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func()
         .create("int1", "Interpolation");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func()
         .create("int2", "Interpolation");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func()
         .create("int3", "Interpolation");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func()
         .create("int5", "Interpolation");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func()
         .create("int6", "Interpolation");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func()
         .create("int8", "Interpolation");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func()
         .create("int10", "Interpolation");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func()
         .create("int11", "Interpolation");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func()
         .create("int12", "Interpolation");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func()
         .create("int13", "Interpolation");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func()
         .create("int14", "Interpolation");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func()
         .create("int15", "Interpolation");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func()
         .create("int16", "Interpolation");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func()
         .create("int17", "Interpolation");
    model.component("comp1").material("mat3").propertyGroup()
         .create("OperationalSOC", "OperationalSOC", "Operational electrode state-of-charge");
    model.component("comp1").material("mat3").propertyGroup().create("ic", "ic", "Intercalation strain");
    model.component("comp1").material("mat4").selection().set(5);
    model.component("comp1").material("mat4").propertyGroup()
         .create("Enu", "Enu", "Young's modulus and Poisson's ratio");
    model.component("comp1").material("mat4").propertyGroup().create("Murnaghan", "Murnaghan", "Murnaghan");
    model.component("comp1").material("mat4").propertyGroup().create("Lame", "Lame", "Lam\u00e9 parameters");
    model.component("comp1").material("mat5").selection().set(1);
    model.component("comp1").material("mat5").propertyGroup()
         .create("Enu", "Enu", "Young's modulus and Poisson's ratio");
    model.component("comp1").material("mat5").propertyGroup().create("linzRes", "linzRes", "Linearized resistivity");

    model.component("comp1").cpl().create("intop1", "Integration");
    model.component("comp1").cpl().create("intop2", "Integration");
    model.component("comp1").cpl().create("intop3", "Integration");
    model.component("comp1").cpl().create("intop4", "Integration");
    model.component("comp1").cpl().create("intop5", "Integration");
    model.component("comp1").cpl().create("aveop1", "Average");
    model.component("comp1").cpl().create("aveop2", "Average");
    model.component("comp1").cpl().create("aveop3", "Average");
    model.component("comp1").cpl().create("aveop4", "Average");
    model.component("comp1").cpl().create("aveop5", "Average");
    model.component("comp1").cpl().create("intop6", "Integration");
    model.component("comp1").cpl().create("aveop6", "Average");
    model.component("comp1").cpl("intop1").selection().set(5);
    model.component("comp1").cpl("intop2").selection().set(2);
    model.component("comp1").cpl("intop3").selection().set(3);
    model.component("comp1").cpl("intop4").selection().set(4);
    model.component("comp1").cpl("intop5").selection().set(1);
    model.component("comp1").cpl("aveop1").selection().set(1);
    model.component("comp1").cpl("aveop2").selection().set(2);
    model.component("comp1").cpl("aveop3").selection().set(3);
    model.component("comp1").cpl("aveop4").selection().set(4);
    model.component("comp1").cpl("aveop5").selection().set(5);
    model.component("comp1").cpl("intop6").selection().geom("geom1", 0);
    model.component("comp1").cpl("intop6").selection().set(5);
    model.component("comp1").cpl("aveop6").selection().set(2, 3, 4);

    model.component("comp1").physics().create("liion", "LithiumIonBatteryMPH", "geom1");
    model.component("comp1").physics("liion").create("ice1", "Electrolyte", 1);
    model.component("comp1").physics("liion").create("init2", "init", 1);
    model.component("comp1").physics("liion").feature("init2").selection().set(1, 4);
    model.component("comp1").physics("liion").create("init4", "init", 1);
    model.component("comp1").physics("liion").feature("init4").selection().set(4);
    model.component("comp1").physics("liion").create("init3", "init", 1);
    model.component("comp1").physics("liion").feature("init3").selection().set(5);
    model.component("comp1").physics("liion").create("pce1", "PorousElectrode", 1);
    model.component("comp1").physics("liion").feature("pce1").selection().set(2);
    model.component("comp1").physics("liion").create("pce2", "PorousElectrode", 1);
    model.component("comp1").physics("liion").feature("pce2").selection().set(4);
    model.component("comp1").physics("liion").create("ece1", "CurrentConductor", 1);
    model.component("comp1").physics("liion").feature("ece1").selection().set(1, 5);
    model.component("comp1").physics("liion").feature("sep1").selection().set();
    model.component("comp1").physics("liion").create("egnd1", "ElectricGround", 0);
    model.component("comp1").physics("liion").feature("egnd1").selection().set(1);
    model.component("comp1").physics("liion").create("ec1", "ElectrodeCurrent", 0);
    model.component("comp1").physics("liion").feature("ec1").selection().set(6);
    model.component("comp1").physics().create("ge", "GlobalEquations", "geom1");
    model.component("comp1").physics("ge").feature("ge1").set("DependentVariableQuantity", "none");
    model.component("comp1").physics("ge").feature("ge1").set("CustomDependentVariableUnit", "Ah");
    model.component("comp1").physics("ge").create("ge2", "GlobalEquations", -1);
    model.component("comp1").physics("ge").feature("ge2").set("DependentVariableQuantity", "none");
    model.component("comp1").physics("ge").feature("ge2").set("CustomDependentVariableUnit", "Wh");
    model.component("comp1").physics().create("ev", "Events", "geom1");
    model.component("comp1").physics("ev").create("ds1", "DiscreteStates", -1);
    model.component("comp1").physics("ev").create("is1", "IndicatorStates", -1);
    model.component("comp1").physics("ev").create("impl1", "ImplicitEvent", -1);
    model.component("comp1").physics("ev").create("impl2", "ImplicitEvent", -1);
    model.component("comp1").physics("ev").create("impl3", "ImplicitEvent", -1);
    model.component("comp1").physics("ev").create("ds2", "DiscreteStates", -1);
    model.component("comp1").physics("ev").create("is2", "IndicatorStates", -1);

    model.component("comp1").mesh("mesh1").create("edg2", "Edge");
    model.component("comp1").mesh("mesh1").feature("edg2").create("size1", "Size");
    model.component("comp1").mesh("mesh1").feature("edg2").feature("size1").selection().geom("geom1", 1);
    model.component("comp1").mesh("mesh1").feature("edg2").feature("size1").selection().set(2, 4);

    model.component("comp1").probe().create("point1", "Point");
    model.component("comp1").probe().create("var1", "GlobalVariable");
    model.component("comp1").probe().create("point2", "Point");
    model.component("comp1").probe("point1").selection().set();
    model.component("comp1").probe("point2").selection().set();

    model.result().table("tbl10").label("\u63a2\u9488\u8868 10");
    model.result().table("tbl12").label("0.25~2pcharge");
    model.result().table("tbl13").label("0.25~2pdis");
    model.result().table("tbl14").comments("\u5168\u5c40\u8ba1\u7b97 2");
    model.result().table("mrkvl1").label("\u6700\u5927\u503c\u548c\u6700\u5c0f\u503c");
    model.result().table("mrkvl1").comments("\u6807\u8bb0");
    model.result().table("tbl22").label("CW391-25");
    model.result().table("tbl31").label("CW391-45");
    model.result().table("tbl32").label("CW511-25");
    model.result().table("tbl33").label("CW511-45");
    model.result().table("tbl29").label("Objective \u8868\u683c 29");
    model.result().table("tbl30").comments("\u5168\u5c40\u8ba1\u7b97 2");

    model.component("comp1").variable("var1").active(false);
    model.component("comp1").variable("var7").label("\u8fc7\u7535\u4f4d\u5206\u89e3-\u53d8\u91cf");

    return model;
  }

  public static Model run2(Model model) {
    model.component("comp1").variable("var2").label("\u8fc7\u7535\u4f4d\u5206\u89e3-\u79ef\u5206");
    model.component("comp1").variable("var3").active(false);
    model.component("comp1").variable("var3").label("\u8fc7\u7535\u4f4d--\u7ebf");
    model.component("comp1").variable("var6").label("\u4ea7\u70ed\u8868\u8fbe\u5f0f");

    model.component("comp1").view("view1").axis().set("xmin", -1.3896729797124863E-5);
    model.component("comp1").view("view1").axis().set("xmax", 2.918314712587744E-4);
    model.view("view4").axis().set("xmin", 0.949999988079071);
    model.view("view4").axis().set("xmax", 2.049999952316284);
    model.view("view4").axis().set("ymin", -528.2001953125);
    model.view("view4").axis().set("ymax", 11114.2001953125);
    model.view("view4").axis().set("viewscaletype", "automatic");
    model.view("view5").set("showgrid", false);
    model.view("view5").axis().set("xmin", 0.9500000476837158);
    model.view("view5").axis().set("xmax", 2.049999952316284);
    model.view("view5").axis().set("ymin", -9.75);
    model.view("view5").axis().set("ymax", 226.75);
    model.view("view5").axis().set("viewscaletype", "automatic");

    model.component("comp1").material("mat1").label("Graphite, LixC6 MCMB (Negative, Li-ion Battery)");
    model.component("comp1").material("mat1").propertyGroup("def").label("Basic");
    model.component("comp1").material("mat1").propertyGroup("def").func("int1").label("Interpolation 1");
    model.component("comp1").material("mat1").propertyGroup("def").func("int1").set("funcname", "E_int");
    model.component("comp1").material("mat1").propertyGroup("def").func("int1")
         .set("table", new String[][]{{"0", "32.47"}, {"0.333", "28.56"}, {"0.5", "58.06"}, {"1", "108.67"}});
    model.component("comp1").material("mat1").propertyGroup("def").func("int1").set("fununit", new String[]{"GPa"});
    model.component("comp1").material("mat1").propertyGroup("def").func("int1").set("argunit", new String[]{"1"});
    model.component("comp1").material("mat1").propertyGroup("def").func("int2").label("Interpolation 2");
    model.component("comp1").material("mat1").propertyGroup("def").func("int2").set("funcname", "nu_int");
    model.component("comp1").material("mat1").propertyGroup("def").func("int2")
         .set("table", new String[][]{{"0", "0.32"}, {"0.333", "0.39"}, {"0.5", "0.34"}, {"1", "0.24"}});
    model.component("comp1").material("mat1").propertyGroup("def").func("int2").set("fununit", new String[]{""});
    model.component("comp1").material("mat1").propertyGroup("def").set("youngsmodulus", "");
    model.component("comp1").material("mat1").propertyGroup("def").set("poissonsratio", "");
    model.component("comp1").material("mat1").propertyGroup("def").set("youngsmodulus", "E_int(c/csmax)");
    model.component("comp1").material("mat1").propertyGroup("def")
         .setPropertyInfo("youngsmodulus", "Yue Qi et al 2010 J. Electrochem. Soc. 157 A558");
    model.component("comp1").material("mat1").propertyGroup("def").set("poissonsratio", "nu_int(c/csmax)");
    model.component("comp1").material("mat1").propertyGroup("def")
         .setPropertyInfo("poissonsratio", "Yue Qi et al 2010 J. Electrochem. Soc. 157 A558");
    model.component("comp1").material("mat1").propertyGroup("def")
         .set("electricconductivity", new String[]{"sigma_neg", "0", "0", "0", "sigma_neg", "0", "0", "0", "sigma_neg"});
    model.component("comp1").material("mat1").propertyGroup("def")
         .setPropertyInfo("electricconductivity", "V. Srinivasan, and J. Newman, \u201cDesign and Optimization of a Natural Graphite/Iron Phosphate Lithium Ion Cell,\u201d J. Electrochem. Soc., vol. 151, p. 1530, 2004.");
    model.component("comp1").material("mat1").propertyGroup("def")
         .set("diffusion", new String[]{"3.9e-12*k_dn", "0", "0", "0", "3.9e-12*k_dn", "0", "0", "0", "3.9e-12*k_dn"});
    model.component("comp1").material("mat1").propertyGroup("def")
         .setPropertyInfo("diffusion", "K. Kumaresan, G. Sikha, and R. E. White, \u201cThermal Model for a Li-Ion Cell,\u201d J. Electrochem. Soc., vol. 155, p. A164, 2008.");
    model.component("comp1").material("mat1").propertyGroup("def")
         .set("thermalconductivity", new String[]{"1[W/(m*K)]", "0", "0", "0", "1[W/(m*K)]", "0", "0", "0", "1[W/(m*K)]"});
    model.component("comp1").material("mat1").propertyGroup("def")
         .setPropertyInfo("thermalconductivity", "S. Chen, C. Wan, and Y. Wang, J. Power Sources, 140, 111 (2005).");
    model.component("comp1").material("mat1").propertyGroup("def").set("heatcapacity", "750[J/(kg*K)]");
    model.component("comp1").material("mat1").propertyGroup("def")
         .setPropertyInfo("heatcapacity", "SI Chemical Data, John Wiley & Sons, 1994");
    model.component("comp1").material("mat1").propertyGroup("def").set("density", "2250[kg/m^3]");
    model.component("comp1").material("mat1").propertyGroup("def")
         .setPropertyInfo("density", "SI Chemical Data, John Wiley & Sons, 1994");
    model.component("comp1").material("mat1").propertyGroup("def").set("T_ref", "318[K]");
    model.component("comp1").material("mat1").propertyGroup("def").descr("T_ref", "");
    model.component("comp1").material("mat1").propertyGroup("def").set("T2", "min(393.15,max(T,223.15))");
    model.component("comp1").material("mat1").propertyGroup("def").descr("T2", "");
    model.component("comp1").material("mat1").propertyGroup("def").set("csmax", "28262.938[mol/m^3]");
    model.component("comp1").material("mat1").propertyGroup("def").descr("csmax", "");
    model.component("comp1").material("mat1").propertyGroup("def").addInput("temperature");
    model.component("comp1").material("mat1").propertyGroup("def").addInput("concentration");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").label("Equilibrium potential");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int1")
         .label("Interpolation 1");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int1")
         .set("funcname", "Eeq_int1");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int1")
         .set("table", new String[][]{{"0", "2.781186612"}, 
         {"0.01", "1.520893224"}, 
         {"0.02", "0.893922607"}, 
         {"0.03", "0.581284406"}, 
         {"0.04", "0.42452844"}, 
         {"0.05", "0.344895805"}, 
         {"0.06", "0.303146342"}, 
         {"0.07", "0.279578072"}, 
         {"0.08", "0.264093089"}, 
         {"0.09", "0.251347845"}, 
         {"0.1", "0.238588379"}, 
         {"0.11", "0.224803164"}, 
         {"0.12", "0.210294358"}, 
         {"0.13", "0.196408586"}, 
         {"0.14", "0.184624188"}, 
         {"0.15", "0.175188157"}, 
         {"0.16", "0.167373311"}, 
         {"0.17", "0.160452107"}, 
         {"0.18", "0.154025412"}, 
         {"0.19", "0.147948522"}, 
         {"0.2", "0.142214997"}, 
         {"0.21", "0.13688271"}, 
         {"0.22", "0.132033114"}, 
         {"0.23", "0.127747573"}, 
         {"0.24", "0.124091616"}, 
         {"0.25", "0.121103387"}, 
         {"0.26", "0.11878567"}, 
         {"0.27", "0.117102317"}, 
         {"0.28", "0.115980205"}, 
         {"0.29", "0.115317054"}, 
         {"0.3", "0.114993965"}, 
         {"0.31", "0.114890105"}, 
         {"0.32", "0.114886278"}, 
         {"0.33", "0.114884619"}, 
         {"0.34", "0.114873068"}, 
         {"0.35", "0.114824904"}, 
         {"0.36", "0.114644725"}, 
         {"0.37", "0.114372614"}, 
         {"0.38", "0.114017954"}, 
         {"0.39", "0.11359371"}, 
         {"0.4", "0.11311133"}, 
         {"0.41", "0.112575849"}, 
         {"0.42", "0.111980245"}, 
         {"0.43", "0.111297682"}, 
         {"0.44", "0.110470149"}, 
         {"0.45", "0.109393081"}, 
         {"0.46", "0.107900592"}, 
         {"0.47", "0.10576964"}, 
         {"0.48", "0.102783317"}, 
         {"0.49", "0.09889031"}, 
         {"0.5", "0.094391564"}, 
         {"0.51", "0.089921069"}, 
         {"0.52", "0.086112415"}, 
         {"0.53", "0.083265315"}, 
         {"0.54", "0.081326247"}, 
         {"0.55", "0.080074892"}, 
         {"0.56", "0.07928329"}, 
         {"0.57", "0.078778765"}, 
         {"0.58", "0.078447703"}, 
         {"0.59", "0.078220432"}, 
         {"0.6", "0.078055641"}, 
         {"0.61", "0.077929111"}, 
         {"0.62", "0.077826563"}, 
         {"0.63", "0.077739397"}, 
         {"0.64", "0.077662227"}, 
         {"0.65", "0.077591472"}, 
         {"0.66", "0.077524557"}, 
         {"0.67", "0.077459463"}, 
         {"0.68", "0.077394455"}, 
         {"0.69", "0.077327934"}, 
         {"0.7", "0.077258337"}, 
         {"0.71", "0.077184077"}, 
         {"0.72", "0.077103499"}, 
         {"0.73", "0.077014851"}, 
         {"0.74", "0.076916258"}, 
         {"0.75", "0.07680571"}, 
         {"0.76", "0.07668104"}, 
         {"0.77", "0.07653992"}, 
         {"0.78", "0.076379839"}, 
         {"0.79", "0.076198086"}, 
         {"0.8", "0.075991699"}, 
         {"0.81", "0.075757371"}, 
         {"0.82", "0.075491288"}, 
         {"0.83", "0.075188813"}, 
         {"0.84", "0.07484398"}, 
         {"0.85", "0.074448647"}, 
         {"0.86", "0.07399118"}, 
         {"0.87", "0.073454466"}, 
         {"0.88", "0.072812991"}, 
         {"0.89", "0.072028722"}, 
         {"0.9", "0.071045433"}, 
         {"0.91", "0.069780996"}, 
         {"0.92", "0.068116222"}, 
         {"0.93", "0.065874599"}, 
         {"0.94", "0.062770873"}, 
         {"0.95", "0.058253898"}, 
         {"0.96", "0.051075794"}, 
         {"0.97", "0.038790069"}, 
         {"0.98", "0.020172191"}});
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int1")
         .set("interp", "piecewisecubic");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int1")
         .set("extrap", "linear");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int1")
         .set("fununit", new String[]{"V"});
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int1")
         .set("argunit", new String[]{""});
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int2")
         .label("Interpolation 2");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int2")
         .set("funcname", "dEeqdT_int1");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int2")
         .set("table", new String[][]{{"0", "3.0e-4"}, 
         {"0.17", "0"}, 
         {"0.24", "-6e-5"}, 
         {"0.28", "-1.6e-4"}, 
         {"0.5", "-1.6e-4"}, 
         {"0.54", "-9e-5"}, 
         {"0.71", "-9e-5"}, 
         {"0.85", "-1.0e-4"}, 
         {"1.0", "-1.2e-4"}});
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int2")
         .set("fununit", new String[]{"V/K"});
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int2")
         .set("argunit", new String[]{""});
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("an1")
         .set("funcname", "Eeq_int323");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("an1")
         .set("expr", "0.6379+0.5416*exp(-305.5309*x)+0.044*tanh(-(x-0.1958)/0.1088)-0.1978*tanh((x-1.0571)/0.0854)-0.6875*tanh((x+0.0117)/0.0529)-0.0175*tanh((x-0.5692)/0.0875)");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("an1").set("fununit", "V");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int3")
         .set("funcname", "Eeq_int33");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int3")
         .set("table", new String[][]{{"0", "1.0094"}, 
         {"0.00121", "0.8147"}, 
         {"0.00243", "0.7417"}, 
         {"0.00364", "0.6907"}, 
         {"0.00485", "0.6532"}, 
         {"0.00607", "0.6224"}, 
         {"0.00728", "0.5954"}, 
         {"0.0085", "0.5714"}, 
         {"0.00971", "0.5498"}, 
         {"0.01092", "0.53"}, 
         {"0.01244", "0.5118"}, 
         {"0.01365", "0.4948"}, 
         {"0.01487", "0.4791"}, 
         {"0.01608", "0.4646"}, 
         {"0.01729", "0.4506"}, 
         {"0.01851", "0.4376"}, 
         {"0.01972", "0.4252"}, 
         {"0.02093", "0.4136"}, 
         {"0.02215", "0.4024"}, 
         {"0.02336", "0.3919"}, 
         {"0.02488", "0.3816"}, 
         {"0.02609", "0.3719"}, 
         {"0.02731", "0.3627"}, 
         {"0.02852", "0.3537"}, 
         {"0.02973", "0.3454"}, 
         {"0.03095", "0.3371"}, 
         {"0.03216", "0.3291"}, 
         {"0.03337", "0.3216"}, 
         {"0.03459", "0.3142"}, 
         {"0.0358", "0.3069"}, 
         {"0.03732", "0.2999"}, 
         {"0.03853", "0.2934"}, 
         {"0.03975", "0.2869"}, 
         {"0.04096", "0.2804"}, 
         {"0.04217", "0.2742"}, 
         {"0.04339", "0.2682"}, 
         {"0.0446", "0.2623"}, 
         {"0.04581", "0.2565"}, 
         {"0.04703", "0.251"}, 
         {"0.04854", "0.2458"}, 
         {"0.04976", "0.2404"}, 
         {"0.05097", "0.2353"}, 
         {"0.05218", "0.2303"}, 
         {"0.0534", "0.2255"}, 
         {"0.05461", "0.2209"}, 
         {"0.05583", "0.2164"}, 
         {"0.05704", "0.2122"}, 
         {"0.05825", "0.2082"}, 
         {"0.05977", "0.2045"}, 
         {"0.06098", "0.2015"}, 
         {"0.0622", "0.199"}, 
         {"0.06341", "0.1972"}, 
         {"0.06462", "0.1959"}, 
         {"0.06584", "0.1948"}, 
         {"0.06705", "0.1942"}, 
         {"0.06826", "0.1936"}, 
         {"0.06948", "0.1931"}, 
         {"0.07069", "0.1927"}, 
         {"0.07221", "0.1924"}, 
         {"0.07342", "0.1921"}, 
         {"0.07464", "0.1917"}, 
         {"0.07585", "0.1914"}, 
         {"0.07706", "0.1911"}, 
         {"0.07828", "0.1908"}, 
         {"0.07949", "0.1905"}, 
         {"0.0807", "0.1902"}, 
         {"0.08192", "0.1899"}, 
         {"0.08343", "0.1896"}, 
         {"0.08465", "0.1893"}, 
         {"0.08586", "0.189"}, 
         {"0.08708", "0.1886"}, 
         {"0.08829", "0.1883"}, 
         {"0.0895", "0.1879"}, 
         {"0.09072", "0.1876"}, 
         {"0.09193", "0.1873"}, 
         {"0.09314", "0.1868"}, 
         {"0.09436", "0.1865"}, 
         {"0.09587", "0.186"}, 
         {"0.09709", "0.1857"}, 
         {"0.0983", "0.1852"}, 
         {"0.09951", "0.1849"}, 
         {"0.10073", "0.1845"}, 
         {"0.10194", "0.184"}, 
         {"0.10316", "0.1835"}, 
         {"0.10437", "0.1831"}, 
         {"0.10983", "0.1817"}, 
         {"0.11135", "0.1809"}, 
         {"0.11286", "0.1801"}, 
         {"0.11408", "0.1793"}, 
         {"0.11559", "0.1786"}, 
         {"0.11681", "0.1778"}, 
         {"0.11833", "0.1772"}, 
         {"0.11984", "0.1764"}, 
         {"0.12106", "0.1756"}, 
         {"0.12257", "0.1747"}, 
         {"0.12379", "0.1739"}, 
         {"0.1253", "0.173"}, 
         {"0.12682", "0.1722"}, 
         {"0.12803", "0.1711"}, 
         {"0.12955", "0.1702"}, 
         {"0.13076", "0.1694"}, 
         {"0.13228", "0.1683"}, 
         {"0.1335", "0.1674"}, 
         {"0.13501", "0.1665"}, 
         {"0.13623", "0.1654"}, 
         {"0.13774", "0.1645"}, 
         {"0.13896", "0.1635"}, 
         {"0.14047", "0.1625"}, 
         {"0.14199", "0.1614"}, 
         {"0.14351", "0.1604"}, 
         {"0.14472", "0.1594"}, 
         {"0.14624", "0.1584"}, 
         {"0.14745", "0.1575"}, 
         {"0.14897", "0.1564"}, 
         {"0.15049", "0.1556"}, 
         {"0.1517", "0.1547"}, 
         {"0.15322", "0.1538"}, 
         {"0.15443", "0.1531"}, 
         {"0.15595", "0.1522"}, 
         {"0.15716", "0.1514"}, 
         {"0.15868", "0.1505"}, 
         {"0.16019", "0.1497"}, 
         {"0.16141", "0.1488"}, 
         {"0.16292", "0.148"}, 
         {"0.16444", "0.1471"}, 
         {"0.16566", "0.1462"}, 
         {"0.16717", "0.1452"}, 
         {"0.16869", "0.1443"}, 
         {"0.1699", "0.1434"}, 
         {"0.17142", "0.1426"}, 
         {"0.17263", "0.1417"}, 
         {"0.17415", "0.1409"}, 
         {"0.17536", "0.14"}, 
         {"0.17688", "0.1392"}, 
         {"0.17809", "0.1384"}, 
         {"0.17961", "0.1376"}, 
         {"0.18083", "0.1369"}, 
         {"0.18234", "0.1361"}, 
         {"0.18386", "0.1355"}, 
         {"0.18507", "0.1347"}, 
         {"0.18659", "0.1339"}, 
         {"0.1878", "0.1333"}, 
         {"0.18932", "0.1325"}, 
         {"0.19053", "0.1318"}, 
         {"0.19205", "0.1311"}, 
         {"0.19357", "0.1304"}, 
         {"0.19478", "0.1296"}, 
         {"0.1963", "0.1291"}, 
         {"0.19782", "0.1282"}, 
         {"0.19903", "0.1276"}, 
         {"0.20055", "0.1266"}, 
         {"0.20206", "0.1259"}, 
         {"0.20328", "0.1252"}, 
         {"0.20479", "0.1245"}, 
         {"0.20601", "0.1239"}, 
         {"0.20752", "0.1231"}, 
         {"0.21299", "0.1220"}, 
         {"0.2145", "0.1208"}, 
         {"0.21572", "0.1203"}, 
         {"0.21723", "0.1194"}, 
         {"0.21845", "0.1186"}, 
         {"0.21996", "0.1177"}, 
         {"0.22118", "0.1169"}, 
         {"0.22269", "0.1163"}, 
         {"0.22421", "0.1155"}, 
         {"0.22542", "0.1149"}, 
         {"0.22664", "0.1142"}, 
         {"0.22816", "0.1138"}, 
         {"0.22937", "0.1132"}, 
         {"0.23089", "0.1127"}, 
         {"0.2321", "0.1121"}, 
         {"0.23362", "0.1118"}, 
         {"0.23483", "0.1113"}, 
         {"0.23635", "0.111"}, 
         {"0.23756", "0.1107"}, 
         {"0.23908", "0.1104"}, 
         {"0.24029", "0.1101"}, 
         {"0.24181", "0.1097"}, 
         {"0.24302", "0.1096"}, 
         {"0.24424", "0.1094"}, 
         {"0.24575", "0.1093"}, 
         {"0.24697", "0.1091"}, 
         {"0.24848", "0.1088"}, 
         {"0.2497", "0.1087"}, 
         {"0.25121", "0.1085"}, 
         {"0.25243", "0.1084"}, 
         {"0.25364", "0.1082"}, 
         {"0.25516", "0.108"}, 
         {"0.25637", "0.1077"}, 
         {"0.25789", "0.1074"}, 
         {"0.2591", "0.1073"}, 
         {"0.26062", "0.107"}, 
         {"0.26183", "0.1066"}, 
         {"0.26335", "0.1065"}, 
         {"0.26456", "0.1062"}, 
         {"0.26608", "0.106"}, 
         {"0.26729", "0.1057"}, 
         {"0.26881", "0.1056"}, 
         {"0.27002", "0.1054"}, 
         {"0.27154", "0.1053"}, 
         {"0.28914", "0.1039"}, 
         {"0.29187", "0.1037"}, 
         {"0.29339", "0.1035"}, 
         {"0.30006", "0.1034"}, 
         {"0.30431", "0.1032"}, 
         {"0.30977", "0.1031"}, 
         {"0.32191", "0.1026"}, 
         {"0.32312", "0.1023"}, 
         {"0.32585", "0.1022"}, 
         {"0.3301", "0.102"}, 
         {"0.33404", "0.1018"}, 
         {"0.34072", "0.1017"}, 
         {"0.37075", "0.1017"}, 
         {"0.37773", "0.1014"}, 
         {"0.37894", "0.1012"}, 
         {"0.38046", "0.1012"}, 
         {"0.38167", "0.1011"}, 
         {"0.38319", "0.1009"}, 
         {"0.38441", "0.1009"}, 
         {"0.38562", "0.1008"}, 
         {"0.38714", "0.1008"}, 
         {"0.38835", "0.1006"}, 
         {"0.38987", "0.1004"}, 
         {"0.39108", "0.1004"}, 
         {"0.3926", "0.1003"}, 
         {"0.39381", "0.1003"}, 
         {"0.39533", "0.1001"}, 
         {"0.39654", "0.1"}, 
         {"0.39806", "0.1"}, 
         {"0.39927", "0.0998"}, 
         {"0.40079", "0.0997"}, 
         {"0.402", "0.0997"}, 
         {"0.40352", "0.0995"}, 
         {"0.40473", "0.0994"}, 
         {"0.40625", "0.0994"}, 
         {"0.40746", "0.0992"}, 
         {"0.40898", "0.0991"}, 
         {"0.41019", "0.0989"}, 
         {"0.41171", "0.0987"}, 
         {"0.41292", "0.0987"}, 
         {"0.41444", "0.0986"}, 
         {"0.41566", "0.0984"}, 
         {"0.41717", "0.0984"}, 
         {"0.41839", "0.0983"}, 
         {"0.42658", "0.098"}, 
         {"0.42779", "0.0977"}, 
         {"0.42931", "0.0975"}, 
         {"0.43052", "0.0973"}, 
         {"0.43204", "0.0973"}, 
         {"0.43325", "0.0973"}, 
         {"0.43477", "0.0972"}, 
         {"0.43598", "0.0972"}, 
         {"0.4375", "0.0972"}, 
         {"0.43871", "0.0972"}, 
         {"0.44023", "0.097"}, 
         {"0.44144", "0.097"}, 
         {"0.44296", "0.0969"}, 
         {"0.44417", "0.0967"}, 
         {"0.44569", "0.0966"}, 
         {"0.44691", "0.0964"}, 
         {"0.44842", "0.0963"}, 
         {"0.44964", "0.0961"}, 
         {"0.45115", "0.096"}, 
         {"0.45237", "0.0958"}, 
         {"0.45388", "0.0956"}, 
         {"0.4551", "0.0955"}, 
         {"0.45661", "0.0952"}, 
         {"0.45783", "0.095"}, 
         {"0.45934", "0.0949"}, 
         {"0.46056", "0.0947"}, 
         {"0.46208", "0.0946"}, 
         {"0.46329", "0.0942"}, 
         {"0.46481", "0.0941"}, 
         {"0.46602", "0.0938"}, 
         {"0.46754", "0.0936"}, 
         {"0.46875", "0.0935"}, 
         {"0.47027", "0.0932"}, 
         {"0.47148", "0.0929"}, 
         {"0.473", "0.0927"}, 
         {"0.47421", "0.0925"}, 
         {"0.47573", "0.0922"}, 
         {"0.47694", "0.0921"}, 
         {"0.47846", "0.0919"}, 
         {"0.47967", "0.0918"}, 
         {"0.48119", "0.0916"}, 
         {"0.4824", "0.0915"}, 
         {"0.48392", "0.0913"}, 
         {"0.48513", "0.0911"}, 
         {"0.48665", "0.091"}, 
         {"0.48786", "0.091"}, 
         {"0.48938", "0.0908"}, 
         {"0.49059", "0.0907"}, 
         {"0.49181", "0.0905"}, 
         {"0.49333", "0.0904"}, 
         {"0.49454", "0.0901"}, 
         {"0.49606", "0.0899"}, 
         {"0.49727", "0.0896"}, 
         {"0.49879", "0.0893"}, 
         {"0.5", "0.089"}, 
         {"0.50152", "0.0887"}, 
         {"0.50273", "0.0884"}, 
         {"0.50425", "0.088"}, 
         {"0.50546", "0.0877"}, 
         {"0.50698", "0.0873"}, 
         {"0.50819", "0.087"}, 
         {"0.50971", "0.0867"}, 
         {"0.51092", "0.0862"}, 
         {"0.51244", "0.0859"}, 
         {"0.51365", "0.0854"}, 
         {"0.51517", "0.0849"}, 
         {"0.51638", "0.0845"}, 
         {"0.5179", "0.084"}, 
         {"0.51911", "0.0836"}, 
         {"0.52063", "0.0831"}, 
         {"0.52184", "0.0826"}, 
         {"0.52336", "0.0823"}, 
         {"0.53823", "0.0801"}, 
         {"0.53944", "0.0798"}, 
         {"0.54096", "0.0794"}, 
         {"0.54217", "0.0786"}, 
         {"0.54369", "0.0778"}, 
         {"0.5449", "0.0772"}, 
         {"0.54642", "0.0764"}, 
         {"0.54763", "0.0758"}, 
         {"0.54915", "0.075"}, 
         {"0.55036", "0.0744"}, 
         {"0.55188", "0.0738"}, 
         {"0.55309", "0.0733"}, 
         {"0.55461", "0.0727"}, 
         {"0.55583", "0.0722"}, 
         {"0.55734", "0.0718"}, 
         {"0.55856", "0.0713"}, 
         {"0.56007", "0.0708"}, 
         {"0.56129", "0.0705"}, 
         {"0.5628", "0.0701"}, 
         {"0.56402", "0.0699"}, 
         {"0.56553", "0.0696"}, 
         {"0.56675", "0.0693"}, 
         {"0.56826", "0.0691"}, 
         {"0.56948", "0.069"}, 
         {"0.571", "0.0688"}, 
         {"0.57221", "0.0687"}, 
         {"0.57373", "0.0687"}, 
         {"0.57494", "0.0685"}, 
         {"0.57646", "0.0685"}, 
         {"0.57767", "0.0685"}, 
         {"0.57919", "0.0685"}, 
         {"0.5804", "0.0685"}, 
         {"0.58192", "0.0685"}, 
         {"0.58313", "0.0685"}, 
         {"0.58465", "0.0685"}, 
         {"0.58586", "0.0685"}, 
         {"0.58738", "0.0685"}, 
         {"0.58859", "0.0685"}, 
         {"0.59011", "0.0684"}, 
         {"0.59132", "0.0684"}, 
         {"0.59284", "0.0684"}, 
         {"0.59405", "0.0682"}, 
         {"0.59557", "0.0682"}, 
         {"0.59678", "0.0682"}, 
         {"0.5983", "0.068"}, 
         {"0.59951", "0.068"}, 
         {"0.60073", "0.0679"}, 
         {"0.60225", "0.0679"}, 
         {"0.60346", "0.0677"}, 
         {"0.60498", "0.0676"}, 
         {"0.60619", "0.0676"}, 
         {"0.60771", "0.0676"}, 
         {"0.60892", "0.0674"}, 
         {"0.61044", "0.0674"}, 
         {"0.61165", "0.0673"}, 
         {"0.61317", "0.0673"}, 
         {"0.61438", "0.0671"}, 
         {"0.6159", "0.0671"}, 
         {"0.61711", "0.067"}, 
         {"0.61863", "0.067"}, 
         {"0.61984", "0.067"}, 
         {"0.62136", "0.0668"}, 
         {"0.62257", "0.0668"}, 
         {"0.62409", "0.0667"}, 
         {"0.6253", "0.0667"}, 
         {"0.62682", "0.0665"}, 
         {"0.62803", "0.0665"}, 
         {"0.63623", "0.0662"}, 
         {"0.63744", "0.066"}, 
         {"0.63896", "0.0659"}, 
         {"0.64017", "0.0657"}, 
         {"0.64169", "0.0656"}, 
         {"0.6429", "0.0654"}, 
         {"0.64442", "0.0653"}, 
         {"0.64563", "0.0651"}, 
         {"0.64715", "0.0651"}, 
         {"0.64836", "0.0649"}, 
         {"0.64988", "0.0648"}, 
         {"0.65109", "0.0648"}, 
         {"0.65261", "0.0648"}, 
         {"0.65382", "0.0646"}, 
         {"0.65534", "0.0646"}, 
         {"0.65655", "0.0646"}, 
         {"0.65807", "0.0645"}, 
         {"0.65928", "0.0645"}, 
         {"0.69751", "0.0645"}, 
         {"0.69873", "0.0643"}, 
         {"0.70024", "0.0643"}, 
         {"0.70146", "0.0642"}, 
         {"0.70297", "0.064"}, 
         {"0.70419", "0.064"}, 
         {"0.7057", "0.0639"}, 
         {"0.70692", "0.0639"}, 
         {"0.70843", "0.0637"}, 
         {"0.70965", "0.0637"}, 
         {"0.71117", "0.0636"}, 
         {"0.71238", "0.0634"}, 
         {"0.7139", "0.0634"}, 
         {"0.71511", "0.0634"}, 
         {"0.71663", "0.0634"}, 
         {"0.71784", "0.0634"}, 
         {"0.71936", "0.0634"}, 
         {"0.72057", "0.0634"}, 
         {"0.72209", "0.0634"}, 
         {"0.7233", "0.0634"}, 
         {"0.72482", "0.0634"}, 
         {"0.75789", "0.0632"}, 
         {"0.7591", "0.0631"}, 
         {"0.76032", "0.0629"}, 
         {"0.76183", "0.0628"}, 
         {"0.76305", "0.0625"}, 
         {"0.76426", "0.0623"}, 
         {"0.76578", "0.0622"}, 
         {"0.76699", "0.062"}, 
         {"0.76851", "0.0618"}, 
         {"0.76972", "0.0615"}, 
         {"0.77093", "0.0614"}, 
         {"0.77245", "0.0612"}, 
         {"0.77367", "0.0611"}, 
         {"0.77488", "0.0609"}, 
         {"0.7764", "0.0608"}, 
         {"0.77761", "0.0606"}, 
         {"0.77882", "0.0605"}, 
         {"0.78034", "0.0603"}, 
         {"0.78155", "0.0601"}, 
         {"0.78277", "0.06"}, 
         {"0.78428", "0.0598"}, 
         {"0.7855", "0.0597"}, 
         {"0.78671", "0.0595"}, 
         {"0.78823", "0.0594"}, 
         {"0.78944", "0.0592"}, 
         {"0.79066", "0.0592"}, 
         {"0.79217", "0.0591"}, 
         {"0.79339", "0.0589"}, 
         {"0.7946", "0.0589"}, 
         {"0.79612", "0.0587"}, 
         {"0.79733", "0.0587"}, 
         {"0.79854", "0.0587"}, 
         {"0.80006", "0.0587"}, 
         {"0.80127", "0.0587"}, 
         {"0.80249", "0.0586"}, 
         {"0.804", "0.0586"}, 
         {"0.80522", "0.0586"}, 
         {"0.81857", "0.0586"}, 
         {"0.81978", "0.0584"}, 
         {"0.821", "0.0584"}, 
         {"0.82251", "0.0583"}, 
         {"0.82373", "0.0581"}, 
         {"0.82494", "0.058"}, 
         {"0.82646", "0.0578"}, 
         {"0.82767", "0.0577"}, 
         {"0.82888", "0.0575"}, 
         {"0.8304", "0.0574"}, 
         {"0.83161", "0.0572"}, 
         {"0.83283", "0.057"}, 
         {"0.83434", "0.057"}, 
         {"0.83556", "0.0569"}, 
         {"0.83677", "0.0567"}, 
         {"0.86833", "0.056"}, 
         {"0.86984", "0.0555"}, 
         {"0.87106", "0.0552"}, 
         {"0.87257", "0.0547"}, 
         {"0.87379", "0.0543"}, 
         {"0.875", "0.0538"}, 
         {"0.87652", "0.0533"}, 
         {"0.87773", "0.053"}, 
         {"0.87894", "0.0525"}, 
         {"0.88046", "0.0521"}, 
         {"0.88167", "0.0518"}, 
         {"0.88289", "0.0513"}, 
         {"0.88441", "0.0508"}, 
         {"0.88562", "0.0505"}, 
         {"0.88683", "0.0502"}, 
         {"0.88835", "0.0499"}, 
         {"0.88956", "0.0496"}, 
         {"0.89078", "0.0493"}, 
         {"0.89229", "0.0491"}, 
         {"0.89351", "0.0488"}, 
         {"0.89472", "0.0487"}, 
         {"0.89624", "0.0484"}, 
         {"0.89745", "0.0482"}, 
         {"0.89867", "0.0481"}, 
         {"0.90018", "0.0477"}, 
         {"0.9014", "0.0476"}, 
         {"0.90261", "0.0474"}, 
         {"0.90413", "0.0473"}, 
         {"0.90534", "0.047"}, 
         {"0.90655", "0.0468"}, 
         {"0.90807", "0.0465"}, 
         {"0.90928", "0.0462"}, 
         {"0.9105", "0.0459"}, 
         {"0.91201", "0.0456"}, 
         {"0.91323", "0.0453"}, 
         {"0.91444", "0.0448"}, 
         {"0.91566", "0.0445"}, 
         {"0.91717", "0.044"}, 
         {"0.91839", "0.0436"}, 
         {"0.9196", "0.0431"}, 
         {"0.92081", "0.0428"}, 
         {"0.92203", "0.0423"}, 
         {"0.92324", "0.0419"}, 
         {"0.92476", "0.0414"}, 
         {"0.92597", "0.0409"}, 
         {"0.92718", "0.0405"}, 
         {"0.9284", "0.0398"}, 
         {"0.92961", "0.0394"}, 
         {"0.93113", "0.0389"}, 
         {"0.93234", "0.0383"}, 
         {"0.93356", "0.0378"}, 
         {"0.93477", "0.0372"}, 
         {"0.93598", "0.0367"}, 
         {"0.9375", "0.0363"}, 
         {"0.93871", "0.0358"}, 
         {"0.93993", "0.0353"}, 
         {"0.94114", "0.0349"}, 
         {"0.98877", "0.0208"}, 
         {"0.99029", "0.0189"}, 
         {"0.9912", "0.0174"}, 
         {"0.99242", "0.0157"}, 
         {"0.99393", "0.0138"}, 
         {"0.99515", "0.0121"}, 
         {"0.99636", "0.0102"}, 
         {"0.99757", "0.0087"}, 
         {"0.99879", "0.0068"}});
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int3")
         .set("extrap", "linear");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int3")
         .set("fununit", new String[]{"V"});

    return model;
  }

  public static Model run3(Model model) {
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int4")
         .set("table", new String[][]{{"1.42E-03", "1.03E+00"}, 
         {"4.05E-03", "9.43E-01"}, 
         {"5.33E-03", "8.72E-01"}, 
         {"6.64E-03", "8.22E-01"}, 
         {"7.97E-03", "7.83E-01"}, 
         {"1.07E-02", "7.43E-01"}, 
         {"1.33E-02", "6.65E-01"}, 
         {"1.60E-02", "6.20E-01"}, 
         {"2.28E-02", "5.31E-01"}, 
         {"2.96E-02", "4.69E-01"}, 
         {"3.77E-02", "4.04E-01"}, 
         {"4.73E-02", "3.50E-01"}, 
         {"5.28E-02", "3.22E-01"}, 
         {"5.83E-02", "2.98E-01"}, 
         {"6.51E-02", "2.67E-01"}, 
         {"6.92E-02", "2.56E-01"}, 
         {"7.20E-02", "2.44E-01"}, 
         {"7.61E-02", "2.33E-01"}, 
         {"8.16E-02", "2.15E-01"}, 
         {"8.71E-02", "2.07E-01"}, 
         {"9.67E-02", "2.04E-01"}, 
         {"1.04E-01", "2.02E-01"}, 
         {"1.12E-01", "2.00E-01"}, 
         {"1.19E-01", "2.00E-01"}, 
         {"1.24E-01", "1.98E-01"}, 
         {"1.30E-01", "1.96E-01"}, 
         {"1.35E-01", "1.93E-01"}, 
         {"1.41E-01", "1.91E-01"}, 
         {"1.46E-01", "1.87E-01"}, 
         {"1.53E-01", "1.81E-01"}, 
         {"1.61E-01", "1.76E-01"}, 
         {"1.72E-01", "1.69E-01"}, 
         {"1.83E-01", "1.61E-01"}, 
         {"1.94E-01", "1.54E-01"}, 
         {"2.08E-01", "1.46E-01"}, 
         {"2.15E-01", "1.43E-01"}, 
         {"2.25E-01", "1.37E-01"}, 
         {"2.34E-01", "1.31E-01"}, 
         {"2.44E-01", "1.26E-01"}, 
         {"2.52E-01", "1.24E-01"}, 
         {"2.62E-01", "1.22E-01"}, 
         {"2.74E-01", "1.22E-01"}, 
         {"2.81E-01", "1.19E-01"}, 
         {"2.88E-01", "1.19E-01"}, 
         {"2.98E-01", "1.17E-01"}, 
         {"3.10E-01", "1.17E-01"}, 
         {"3.25E-01", "1.17E-01"}, 
         {"3.39E-01", "1.15E-01"}, 
         {"4.08E-01", "1.15E-01"}, 
         {"4.64E-01", "1.11E-01"}, 
         {"4.99E-01", "1.09E-01"}, 
         {"5.22E-01", "1.07E-01"}, 
         {"5.35E-01", "1.04E-01"}, 
         {"5.44E-01", "1.00E-01"}, 
         {"5.57E-01", "9.26E-02"}, 
         {"5.65E-01", "8.52E-02"}, 
         {"5.74E-01", "8.15E-02"}, 
         {"6.70E-01", "7.96E-02"}, 
         {"7.77E-01", "7.96E-02"}, 
         {"8.64E-01", "7.78E-02"}, 
         {"9.34E-01", "7.22E-02"}, 
         {"9.45E-01", "7.04E-02"}, 
         {"9.56E-01", "6.67E-02"}, 
         {"9.64E-01", "6.30E-02"}, 
         {"9.74E-01", "5.93E-02"}, 
         {"9.82E-01", "5.37E-02"}, 
         {"9.88E-01", "4.81E-02"}, 
         {"9.92E-01", "4.26E-02"}, 
         {"9.99E-01", "3.52E-02"}, 
         {"1.00E+00", "2.96E-02"}, 
         {"1.01E+00", "2.41E-02"}, 
         {"1.01E+00", "1.48E-02"}, 
         {"1.02E+00", "7.41E-03"}, 
         {"1.02E+00", "1.85E-03"}});
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int5")
         .label("1218GraOCV  0-0.98");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int5")
         .set("funcname", "Eeq_int5");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int5")
         .set("table", new String[][]{{"0.005", "1.15131"}, 
         {"0.00696", "0.87429"}, 
         {"0.00893", "0.75866"}, 
         {"0.01089", "0.68884"}, 
         {"0.01286", "0.6399"}, 
         {"0.01482", "0.59895"}, 
         {"0.01678", "0.56413"}, 
         {"0.01875", "0.53444"}, 
         {"0.02071", "0.50804"}, 
         {"0.02268", "0.48369"}, 
         {"0.02464", "0.46244"}, 
         {"0.0266", "0.44295"}, 
         {"0.02857", "0.42457"}, 
         {"0.03053", "0.40729"}, 
         {"0.03249", "0.3918"}, 
         {"0.03446", "0.37691"}, 
         {"0.03642", "0.36279"}, 
         {"0.03839", "0.35012"}, 
         {"0.04035", "0.33765"}, 
         {"0.04231", "0.32583"}, 
         {"0.04428", "0.31456"}, 
         {"0.04624", "0.30433"}, 
         {"0.04821", "0.29416"}, 
         {"0.05017", "0.28459"}, 
         {"0.05213", "0.27559"}, 
         {"0.0541", "0.26676"}, 
         {"0.05606", "0.2582"}, 
         {"0.05803", "0.25027"}, 
         {"0.05999", "0.24267"}, 
         {"0.06195", "0.23552"}, 
         {"0.06392", "0.22877"}, 
         {"0.06588", "0.22274"}, 
         {"0.06785", "0.21797"}, 
         {"0.06981", "0.2149"}, 
         {"0.07177", "0.21317"}, 
         {"0.07374", "0.21203"}, 
         {"0.0757", "0.21101"}, 
         {"0.07767", "0.21039"}, 
         {"0.07963", "0.20978"}, 
         {"0.08159", "0.20921"}, 
         {"0.08356", "0.20866"}, 
         {"0.08552", "0.20816"}, 
         {"0.08748", "0.20754"}, 
         {"0.08945", "0.20701"}, 
         {"0.09141", "0.20653"}, 
         {"0.09338", "0.20612"}, 
         {"0.09534", "0.20561"}, 
         {"0.0973", "0.20508"}, 
         {"0.09927", "0.20448"}, 
         {"0.10123", "0.20388"}, 
         {"0.1032", "0.20311"}, 
         {"0.10516", "0.20251"}, 
         {"0.10712", "0.20177"}, 
         {"0.10909", "0.20103"}, 
         {"0.11105", "0.2002"}, 
         {"0.11302", "0.1994"}, 
         {"0.11498", "0.19849"}, 
         {"0.11694", "0.19761"}, 
         {"0.11891", "0.19661"}, 
         {"0.12087", "0.19562"}, 
         {"0.12284", "0.19453"}, 
         {"0.1248", "0.19343"}, 
         {"0.12676", "0.19244"}, 
         {"0.12873", "0.19123"}, 
         {"0.13069", "0.18977"}, 
         {"0.13266", "0.18857"}, 
         {"0.13462", "0.18725"}, 
         {"0.13658", "0.18587"}, 
         {"0.13855", "0.18454"}, 
         {"0.14051", "0.18313"}, 
         {"0.14247", "0.18164"}, 
         {"0.14444", "0.18023"}, 
         {"0.1464", "0.17882"}, 
         {"0.14837", "0.17741"}, 
         {"0.15033", "0.17594"}, 
         {"0.15229", "0.17444"}, 
         {"0.15426", "0.17304"}, 
         {"0.15622", "0.17155"}, 
         {"0.15819", "0.1701"}, 
         {"0.16015", "0.16894"}, 
         {"0.16211", "0.16737"}, 
         {"0.16408", "0.1659"}, 
         {"0.16604", "0.16469"}, 
         {"0.16801", "0.16338"}, 
         {"0.16997", "0.16231"}, 
         {"0.17193", "0.16092"}, 
         {"0.1739", "0.15981"}, 
         {"0.17586", "0.15862"}, 
         {"0.17783", "0.15763"}, 
         {"0.17979", "0.15652"}, 
         {"0.18175", "0.15553"}, 
         {"0.18372", "0.15461"}, 
         {"0.18568", "0.15379"}, 
         {"0.18765", "0.15304"}, 
         {"0.18961", "0.15207"}, 
         {"0.19157", "0.15101"}, 
         {"0.19354", "0.15019"}, 
         {"0.1955", "0.14924"}, 
         {"0.19746", "0.14831"}, 
         {"0.19943", "0.14731"}, 
         {"0.20139", "0.14641"}, 
         {"0.20336", "0.14546"}, 
         {"0.20532", "0.14447"}, 
         {"0.20728", "0.14343"}, 
         {"0.20925", "0.14246"}, 
         {"0.21121", "0.14134"}, 
         {"0.21318", "0.14044"}, 
         {"0.21514", "0.13936"}, 
         {"0.2171", "0.13849"}, 
         {"0.21907", "0.13759"}, 
         {"0.22103", "0.1366"}, 
         {"0.223", "0.13584"}, 
         {"0.22496", "0.13501"}, 
         {"0.22692", "0.13441"}, 
         {"0.22889", "0.13371"}, 
         {"0.23085", "0.13321"}, 
         {"0.23282", "0.13281"}, 
         {"0.23478", "0.13213"}, 
         {"0.23674", "0.13171"}, 
         {"0.23871", "0.13121"}, 
         {"0.24067", "0.13071"}, 
         {"0.24264", "0.13031"}, 
         {"0.2446", "0.12988"}, 
         {"0.24656", "0.12938"}, 
         {"0.24853", "0.12894"}, 
         {"0.25049", "0.12841"}, 
         {"0.25245", "0.12801"}, 
         {"0.25442", "0.12761"}, 
         {"0.25638", "0.12701"}, 
         {"0.25835", "0.12667"}, 
         {"0.26031", "0.12617"}, 
         {"0.26227", "0.12581"}, 
         {"0.26424", "0.12551"}, 
         {"0.2662", "0.12521"}, 
         {"0.26817", "0.12501"}, 
         {"0.27013", "0.12491"}, 
         {"0.27209", "0.12471"}, 
         {"0.27406", "0.12468"}, 
         {"0.27602", "0.12451"}, 
         {"0.27799", "0.12451"}, 
         {"0.27995", "0.12451"}, 
         {"0.28191", "0.12451"}, 
         {"0.28388", "0.12451"}, 
         {"0.28584", "0.1245"}, 
         {"0.28781", "0.1245"}, 
         {"0.28977", "0.12441"}, 
         {"0.29173", "0.12441"}, 
         {"0.2937", "0.12441"}, 
         {"0.29566", "0.12441"}, 
         {"0.29763", "0.12436"}, 
         {"0.29959", "0.12421"}, 
         {"0.30155", "0.12421"}, 
         {"0.30352", "0.12421"}, 
         {"0.30548", "0.12421"}, 
         {"0.30744", "0.12412"}, 
         {"0.30941", "0.12411"}, 
         {"0.31137", "0.12411"}, 
         {"0.31334", "0.12411"}, 
         {"0.3153", "0.124"}, 
         {"0.31726", "0.12391"}, 
         {"0.31923", "0.12391"}, 
         {"0.32119", "0.12391"}, 
         {"0.32316", "0.12391"}, 
         {"0.32512", "0.12381"}, 
         {"0.32708", "0.12381"}, 
         {"0.32905", "0.12381"}, 
         {"0.33101", "0.1237"}, 
         {"0.33298", "0.12361"}, 
         {"0.33494", "0.12361"}, 
         {"0.3369", "0.12361"}, 
         {"0.33887", "0.12351"}, 
         {"0.34083", "0.12351"}, 
         {"0.3428", "0.12351"}, 
         {"0.34476", "0.12331"}, 
         {"0.34672", "0.12331"}, 
         {"0.34869", "0.12331"}, 
         {"0.35065", "0.12331"}, 
         {"0.35262", "0.12311"}, 
         {"0.35458", "0.12311"}, 
         {"0.35654", "0.12303"}, 
         {"0.35851", "0.12301"}, 
         {"0.36047", "0.12299"}, 
         {"0.36243", "0.12281"}, 
         {"0.3644", "0.12281"}, 
         {"0.36636", "0.12271"}, 
         {"0.36833", "0.12271"}, 
         {"0.37029", "0.12271"}, 
         {"0.37225", "0.12251"}, 
         {"0.37422", "0.12251"}, 
         {"0.37618", "0.12241"}, 
         {"0.37815", "0.12241"}, 
         {"0.38011", "0.12237"}, 
         {"0.38207", "0.12221"}, 
         {"0.38404", "0.12221"}, 
         {"0.386", "0.12221"}, 
         {"0.38797", "0.12221"}, 
         {"0.38993", "0.12211"}, 
         {"0.39189", "0.12211"}, 
         {"0.39386", "0.12191"}, 
         {"0.39582", "0.12191"}, 
         {"0.39779", "0.12181"}, 
         {"0.39975", "0.12181"}, 
         {"0.40171", "0.12174"}, 
         {"0.40368", "0.12161"}, 
         {"0.40564", "0.12156"}, 
         {"0.40761", "0.12141"}, 
         {"0.40957", "0.12131"}, 
         {"0.41153", "0.12131"}, 
         {"0.4135", "0.12111"}, 
         {"0.41546", "0.1211"}, 
         {"0.41742", "0.12101"}, 
         {"0.41939", "0.12081"}, 
         {"0.42135", "0.12081"}, 
         {"0.42332", "0.12071"}, 
         {"0.42528", "0.12051"}, 
         {"0.42724", "0.12042"}, 
         {"0.42921", "0.12042"}, 
         {"0.43117", "0.12021"}, 
         {"0.43314", "0.12006"}, 
         {"0.4351", "0.12001"}, 
         {"0.43706", "0.11991"}, 
         {"0.43903", "0.11983"}, 
         {"0.44099", "0.11971"}, 
         {"0.44296", "0.11961"}, 
         {"0.44492", "0.11941"}, 
         {"0.44688", "0.11941"}, 
         {"0.44885", "0.11931"}, 
         {"0.45081", "0.11911"}, 
         {"0.45278", "0.11901"}, 
         {"0.45474", "0.11881"}, 
         {"0.4567", "0.11871"}, 
         {"0.45867", "0.11851"}, 
         {"0.46063", "0.11831"}, 
         {"0.4626", "0.11821"}, 
         {"0.46456", "0.11801"}, 
         {"0.46652", "0.11791"}, 
         {"0.46849", "0.11771"}, 
         {"0.47045", "0.11761"}, 
         {"0.47241", "0.11741"}, 
         {"0.47438", "0.11711"}, 
         {"0.47634", "0.11691"}, 
         {"0.47831", "0.11681"}, 
         {"0.48027", "0.11652"}, 
         {"0.48223", "0.11632"}, 
         {"0.4842", "0.11617"}, 
         {"0.48616", "0.11591"}, 
         {"0.48813", "0.11561"}, 
         {"0.49009", "0.11532"}, 
         {"0.49205", "0.11511"}, 
         {"0.49402", "0.11481"}, 
         {"0.49598", "0.11453"}, 
         {"0.49795", "0.11421"}, 
         {"0.49991", "0.11381"}, 
         {"0.50187", "0.11351"}, 
         {"0.50384", "0.11318"}, 
         {"0.5058", "0.11287"}, 
         {"0.50777", "0.11257"}, 
         {"0.50973", "0.11201"}, 
         {"0.51169", "0.11151"}, 
         {"0.51366", "0.11111"}, 
         {"0.51562", "0.11061"}, 
         {"0.51759", "0.11023"}, 
         {"0.51955", "0.1101"}, 
         {"0.52151", "0.10899"}, 
         {"0.52348", "0.10849"}, 
         {"0.52544", "0.10756"}, 
         {"0.5274", "0.1068"}, 
         {"0.52937", "0.10597"}, 
         {"0.53133", "0.10522"}, 
         {"0.5333", "0.10422"}, 
         {"0.53526", "0.10352"}, 
         {"0.53722", "0.10241"}, 
         {"0.53919", "0.10152"}, 
         {"0.54115", "0.10035"}, 
         {"0.54312", "0.09924"}, 
         {"0.54508", "0.09824"}, 
         {"0.54704", "0.09717"}, 
         {"0.54901", "0.096"}, 
         {"0.55097", "0.0951"}, 
         {"0.55294", "0.094"}, 
         {"0.5549", "0.0931"}, 
         {"0.55686", "0.09211"}, 
         {"0.55883", "0.09147"}, 
         {"0.56079", "0.09087"}, 
         {"0.56276", "0.09041"}, 
         {"0.56472", "0.09003"}, 
         {"0.56668", "0.09001"}, 
         {"0.56865", "0.09001"}, 
         {"0.57061", "0.09001"}, 
         {"0.57258", "0.09001"}, 
         {"0.57454", "0.09001"}, 
         {"0.5765", "0.09001"}, 
         {"0.57847", "0.09001"}, 
         {"0.58043", "0.09001"}, 
         {"0.58239", "0.09001"}, 
         {"0.58436", "0.09001"}, 
         {"0.58632", "0.09001"}, 
         {"0.58829", "0.09001"}, 
         {"0.59025", "0.08986"}, 
         {"0.59221", "0.08983"}, 
         {"0.59418", "0.08981"}, 
         {"0.59614", "0.08981"}, 
         {"0.59811", "0.08981"}, 
         {"0.60007", "0.08981"}, 
         {"0.60203", "0.08981"}, 
         {"0.604", "0.08981"}, 
         {"0.60596", "0.08981"}, 
         {"0.60793", "0.08981"}, 
         {"0.60989", "0.08981"}, 
         {"0.61185", "0.08981"}, 
         {"0.61382", "0.08981"}, 
         {"0.61578", "0.08981"}, 
         {"0.61775", "0.08981"}, 
         {"0.61971", "0.08981"}, 
         {"0.62167", "0.08981"}, 
         {"0.62364", "0.08981"}, 
         {"0.6256", "0.08981"}, 
         {"0.62757", "0.08981"}, 
         {"0.62953", "0.08981"}, 
         {"0.63149", "0.08981"}, 
         {"0.63346", "0.08981"}, 
         {"0.63542", "0.08981"}, 
         {"0.63738", "0.08981"}, 
         {"0.63935", "0.08981"}, 
         {"0.64131", "0.08981"}, 
         {"0.64328", "0.0898"}, 
         {"0.64524", "0.0898"}, 
         {"0.6472", "0.08975"}, 
         {"0.64917", "0.08971"}, 
         {"0.65113", "0.08971"}, 
         {"0.6531", "0.08971"}, 
         {"0.65506", "0.08971"}, 
         {"0.65702", "0.08971"}, 
         {"0.65899", "0.08971"}, 
         {"0.66095", "0.08971"}, 
         {"0.66292", "0.08971"}, 
         {"0.66488", "0.08971"}, 
         {"0.66684", "0.08971"}, 
         {"0.66881", "0.08971"}, 
         {"0.67077", "0.08971"}, 
         {"0.67274", "0.08971"}, 
         {"0.6747", "0.08967"}, 
         {"0.67666", "0.08955"}, 
         {"0.67863", "0.08951"}, 
         {"0.68059", "0.08951"}, 
         {"0.68256", "0.08951"}, 
         {"0.68452", "0.08951"}, 
         {"0.68648", "0.08951"}, 
         {"0.68845", "0.08951"}, 
         {"0.69041", "0.08948"}, 
         {"0.69237", "0.08941"}, 
         {"0.69434", "0.08941"}, 
         {"0.6963", "0.08941"}, 
         {"0.69827", "0.08941"}, 
         {"0.70023", "0.08941"}, 
         {"0.70219", "0.08941"}, 
         {"0.70416", "0.0893"}, 
         {"0.70612", "0.08921"}, 
         {"0.70809", "0.08921"}, 
         {"0.71005", "0.08921"}, 
         {"0.71201", "0.08921"}, 
         {"0.71398", "0.08921"}, 
         {"0.71594", "0.08901"}, 
         {"0.71791", "0.08901"}, 
         {"0.71987", "0.08901"}, 
         {"0.72183", "0.08894"}, 
         {"0.7238", "0.08892"}, 
         {"0.72576", "0.08891"}, 
         {"0.72773", "0.08891"}, 
         {"0.72969", "0.08891"}, 
         {"0.73165", "0.08871"}, 
         {"0.73362", "0.08871"}, 
         {"0.73558", "0.08871"}, 
         {"0.73755", "0.08871"}, 
         {"0.73951", "0.08871"}, 
         {"0.74147", "0.08868"}, 
         {"0.74344", "0.08861"}, 
         {"0.7454", "0.08861"}, 
         {"0.74736", "0.08861"}, 
         {"0.74933", "0.08841"}, 
         {"0.75129", "0.08841"}, 
         {"0.75326", "0.08841"}, 
         {"0.75522", "0.08837"}, 
         {"0.75718", "0.08831"}, 
         {"0.75915", "0.08831"}, 
         {"0.76111", "0.08811"}, 
         {"0.76308", "0.08811"}, 
         {"0.76504", "0.08811"}, 
         {"0.767", "0.08801"}, 
         {"0.76897", "0.08801"}, 
         {"0.77093", "0.08801"}, 
         {"0.7729", "0.0879"}, 
         {"0.77486", "0.08781"}, 
         {"0.77682", "0.08769"}, 
         {"0.77879", "0.08761"}, 
         {"0.78075", "0.08761"}, 
         {"0.78272", "0.08751"}, 
         {"0.78468", "0.08751"}, 
         {"0.78664", "0.08751"}, 
         {"0.78861", "0.08751"}, 
         {"0.79057", "0.08731"}, 
         {"0.79254", "0.08731"}, 
         {"0.7945", "0.08721"}, 
         {"0.79646", "0.08721"}, 
         {"0.79843", "0.08717"}, 
         {"0.80039", "0.08701"}, 
         {"0.80235", "0.087"}, 
         {"0.80432", "0.08691"}, 
         {"0.80628", "0.08671"}, 
         {"0.80825", "0.08666"}, 
         {"0.81021", "0.08661"}, 
         {"0.81217", "0.08661"}, 
         {"0.81414", "0.08641"}, 
         {"0.8161", "0.08631"}, 
         {"0.81807", "0.08631"}, 
         {"0.82003", "0.08628"}, 
         {"0.82199", "0.08611"}, 
         {"0.82396", "0.08606"}, 
         {"0.82592", "0.08591"}, 
         {"0.82789", "0.08581"}, 
         {"0.82985", "0.08561"}, 
         {"0.83181", "0.08561"}, 
         {"0.83378", "0.08551"}, 
         {"0.83574", "0.08531"}, 
         {"0.83771", "0.08521"}, 
         {"0.83967", "0.08516"}, 
         {"0.84163", "0.08501"}, 
         {"0.8436", "0.08491"}, 
         {"0.84556", "0.08491"}, 
         {"0.84753", "0.08471"}, 
         {"0.84949", "0.08451"}, 
         {"0.85145", "0.08441"}, 
         {"0.85342", "0.08421"}, 
         {"0.85538", "0.08411"}, 
         {"0.85734", "0.08391"}, 
         {"0.85931", "0.08381"}, 
         {"0.86127", "0.08361"}, 
         {"0.86324", "0.08351"}, 
         {"0.8652", "0.08331"}, 
         {"0.86716", "0.08321"}, 
         {"0.86913", "0.08301"}, 
         {"0.87109", "0.08272"}, 
         {"0.87306", "0.08251"}, 
         {"0.87502", "0.08241"}, 
         {"0.87698", "0.08218"}, 
         {"0.87895", "0.08191"}, 
         {"0.88091", "0.08181"}, 
         {"0.88288", "0.08141"}, 
         {"0.88484", "0.08116"}, 
         {"0.8868", "0.08101"}, 
         {"0.88877", "0.08071"}, 
         {"0.89073", "0.08051"}, 
         {"0.8927", "0.08021"}, 
         {"0.89466", "0.07991"}, 
         {"0.89662", "0.07961"}, 
         {"0.89859", "0.07931"}, 
         {"0.90055", "0.07901"}, 
         {"0.90252", "0.07856"}, 
         {"0.90448", "0.07821"}, 
         {"0.90644", "0.07771"}, 
         {"0.90841", "0.0774"}, 
         {"0.91037", "0.07701"}, 
         {"0.91233", "0.07651"}, 
         {"0.9143", "0.07601"}, 
         {"0.91626", "0.07561"}, 
         {"0.91823", "0.07511"}, 
         {"0.92019", "0.07481"}, 
         {"0.92215", "0.07421"}, 
         {"0.92412", "0.07352"}, 
         {"0.92608", "0.07291"}, 
         {"0.92805", "0.07225"}, 
         {"0.93001", "0.07151"}, 
         {"0.93197", "0.07086"}, 
         {"0.93394", "0.07004"}, 
         {"0.9359", "0.06908"}, 
         {"0.93787", "0.06833"}, 
         {"0.93983", "0.06721"}, 
         {"0.94179", "0.0663"}, 
         {"0.94376", "0.06519"}, 
         {"0.94572", "0.06388"}, 
         {"0.94769", "0.06259"}, 
         {"0.94965", "0.06122"}, 
         {"0.95161", "0.05974"}, 
         {"0.95358", "0.0581"}, 
         {"0.95554", "0.05637"}, 
         {"0.95751", "0.05457"}, 
         {"0.95947", "0.05247"}, 
         {"0.96143", "0.05052"}, 
         {"0.9634", "0.04822"}, 
         {"0.96536", "0.04569"}, 
         {"0.96732", "0.04309"}, 
         {"0.96929", "0.04029"}, 
         {"0.97125", "0.0373"}, 
         {"0.97322", "0.03424"}, 
         {"0.97518", "0.03094"}, 
         {"0.97714", "0.02784"}, 
         {"0.97911", "0.02446"}, 
         {"0.98107", "0.02106"}, 
         {"0.98304", "0.01805"}, 
         {"0.9845", "0.01531"}});
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int5")
         .set("interp", "piecewisecubic");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int5")
         .set("extrap", "linear");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int5")
         .set("fununit", new String[]{"V"});
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int5")
         .set("argunit", new String[]{"1"});
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int6")
         .label("\u6587\u732e\u77f3\u58a8\u5145\u7535");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int6")
         .set("funcname", "Eeq_int7");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int6")
         .set("table", new String[][]{{"8.21846E-4", "1.01098"}, 
         {"0.00107", "0.98342"}, 
         {"0.00109", "0.98166"}, 
         {"0.00111", "0.97993"}, 
         {"0.00112", "0.97822"}, 
         {"0.00121", "0.96999"}, 
         {"0.00123", "0.9684"}, 
         {"0.00125", "0.96684"}, 
         {"0.00126", "0.9653"}, 
         {"0.00128", "0.96377"}, 
         {"0.0013", "0.96227"}, 
         {"0.00151", "0.94546"}, 
         {"0.00154", "0.94321"}, 
         {"0.00202", "0.91455"}, 
         {"0.00256", "0.90497"}, 
         {"0.00327", "0.85917"}, 
         {"0.00346", "0.84425"}, 
         {"0.00457", "0.78281"}, 
         {"0.00459", "0.78218"}, 
         {"0.00491", "0.77011"}, 
         {"0.0056", "0.74277"}, 
         {"0.00632", "0.71872"}, 
         {"0.00653", "0.71191"}, 
         {"0.00716", "0.69239"}, 
         {"0.00763", "0.67779"}, 
         {"0.00785", "0.67141"}, 
         {"0.00931", "0.63063"}, 
         {"0.00961", "0.62291"}, 
         {"0.01012", "0.61015"}, 
         {"0.01212", "0.56572"}, 
         {"0.01287", "0.55217"}, 
         {"0.01403", "0.53423"}, 
         {"0.01753", "0.49289"}, 
         {"0.01874", "0.48157"}, 
         {"0.02112", "0.46038"}, 
         {"0.02342", "0.44129"}, 
         {"0.02657", "0.41765"}, 
         {"0.0288", "0.40222"}, 
         {"0.03152", "0.38466"}, 
         {"0.03458", "0.36553"}, 
         {"0.0354", "0.36068"}, 
         {"0.0379", "0.34678"}, 
         {"0.04112", "0.33023"}, 
         {"0.04461", "0.31352"}, 
         {"0.04983", "0.29075"}, 
         {"0.05407", "0.27425"}, 
         {"0.05919", "0.25777"}, 
         {"0.06249", "0.24906"}, 
         {"0.0683", "0.23714"}, 
         {"0.07582", "0.22732"}, 
         {"0.0836", "0.22269"}, 
         {"0.09137", "0.22082"}, 
         {"0.09915", "0.21879"}, 
         {"0.10692", "0.21698"}, 
         {"0.1147", "0.21415"}, 
         {"0.12247", "0.21063"}, 
         {"0.13025", "0.20681"}, 
         {"0.13803", "0.20281"}, 
         {"0.1458", "0.19888"}, 
         {"0.15358", "0.19517"}, 
         {"0.16135", "0.19175"}, 
         {"0.16913", "0.18854"}, 
         {"0.1769", "0.18543"}, 
         {"0.18468", "0.18238"}, 
         {"0.19245", "0.17951"}, 
         {"0.20023", "0.17689"}, 
         {"0.208", "0.17449"}, 
         {"0.21578", "0.17225"}, 
         {"0.22355", "0.17008"}, 
         {"0.23132", "0.16786"}, 
         {"0.2391", "0.16549"}, 
         {"0.24687", "0.16281"}, 
         {"0.25465", "0.15975"}, 
         {"0.26242", "0.15636"}, 
         {"0.2702", "0.1528"}, 
         {"0.27797", "0.14931"}, 
         {"0.28575", "0.14611"}, 
         {"0.29352", "0.1434"}, 
         {"0.3013", "0.14131"}, 
         {"0.30907", "0.13989"}, 
         {"0.31684", "0.13903"}, 
         {"0.32461", "0.13857"}, 
         {"0.33239", "0.13831"}, 
         {"0.34016", "0.13806"}, 
         {"0.34793", "0.13771"}, 
         {"0.3557", "0.13728"}, 
         {"0.36348", "0.1368"}, 
         {"0.37125", "0.13631"}, 
         {"0.37902", "0.13587"}, 
         {"0.38679", "0.13556"}, 
         {"0.39456", "0.13542"}, 
         {"0.40233", "0.13543"}, 
         {"0.41011", "0.13549"}, 
         {"0.41788", "0.13548"}, 
         {"0.42565", "0.13543"}, 
         {"0.43342", "0.13539"}, 
         {"0.44119", "0.13544"}, 
         {"0.44896", "0.13552"}, 
         {"0.45674", "0.13553"}, 
         {"0.46451", "0.13538"}, 
         {"0.47228", "0.13505"}, 
         {"0.48005", "0.13457"}, 
         {"0.48782", "0.13403"}, 
         {"0.4956", "0.13346"}, 
         {"0.50337", "0.13286"}, 
         {"0.51114", "0.13222"}, 
         {"0.51891", "0.13159"}, 
         {"0.52668", "0.13098"}, 
         {"0.53446", "0.13022"}, 
         {"0.54223", "0.12907"}, 
         {"0.55", "0.12728"}, 
         {"0.55778", "0.12474"}, 
         {"0.56555", "0.12155"}, 
         {"0.57333", "0.11791"}, 
         {"0.58111", "0.11408"}, 
         {"0.58888", "0.11029"}, 
         {"0.59666", "0.10684"}, 
         {"0.60443", "0.10395"}, 
         {"0.61221", "0.10172"}, 
         {"0.61998", "0.10014"}, 
         {"0.62775", "0.09904"}, 
         {"0.63552", "0.09824"}, 
         {"0.64329", "0.09761"}, 
         {"0.65107", "0.0971"}, 
         {"0.65884", "0.09669"}, 
         {"0.66661", "0.09638"}, 
         {"0.67438", "0.09617"}, 
         {"0.68216", "0.09606"}, 
         {"0.68993", "0.09604"}, 
         {"0.6977", "0.09612"}, 
         {"0.70547", "0.09626"}, 
         {"0.71324", "0.09634"}, 
         {"0.72101", "0.09634"}, 
         {"0.72879", "0.09627"}, 
         {"0.73656", "0.09627"}, 
         {"0.74433", "0.09634"}, 
         {"0.7521", "0.09639"}, 
         {"0.75987", "0.09632"}, 
         {"0.76764", "0.09608"}, 
         {"0.77541", "0.09566"}, 
         {"0.784", "0.09505"}, 
         {"0.79096", "0.09451"}, 
         {"0.79873", "0.09384"}, 
         {"0.8065", "0.09319"}, 
         {"0.81428", "0.09263"}, 
         {"0.82205", "0.09225"}, 
         {"0.82982", "0.09209"}, 
         {"0.83759", "0.0921"}, 
         {"0.84536", "0.09215"}, 
         {"0.85313", "0.09218"}, 
         {"0.86091", "0.0922"}, 
         {"0.86868", "0.09223"}, 
         {"0.87645", "0.09219"}, 
         {"0.88422", "0.09204"}, 
         {"0.89199", "0.09175"}, 
         {"0.89977", "0.09131"}, 
         {"0.90754", "0.09072"}, 
         {"0.91531", "0.08994"}, 
         {"0.92308", "0.08894"}, 
         {"0.93086", "0.08754"}, 
         {"0.93863", "0.08567"}, 
         {"0.94641", "0.08217"}, 
         {"0.95418", "0.07677"}, 
         {"0.96196", "0.06975"}, 
         {"0.96974", "0.06119"}, 
         {"0.97752", "0.05106"}, 
         {"0.98378", "0.04175"}, 
         {"0.99045", "0.03066"}, 
         {"0.99422", "0.02386"}, 
         {"0.99919", "0.01427"}});
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int6")
         .set("interp", "piecewisecubic");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int6")
         .set("extrap", "linear");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int6")
         .set("fununit", new String[]{"V"});
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").func("int6")
         .set("argunit", new String[]{"1"});
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").set("Eeq", "Eeq_int5(soc)");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential")
         .setPropertyInfo("Eeq", "D. P Karthikeyan, G. Sikha, and R. E. White, \u201cThermodynamic model development for lithium intercalation electrodes,\u201d J. Power Sources, vol. 185, p. 1398, 2008.");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").set("dEeqdT", "dEeqdT_int1(soc)");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential")
         .setPropertyInfo("dEeqdT", "K. E. Thomas, and J. Newman, \u201cHeats of mixing and of entropy in porous insertion electrodes,\u201d J. Power Sources., vol. 119-121, p. 844, 2003.");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").set("cEeqref", "csmax_neg");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").set("soc", "c/cEeqref");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").descr("soc", "");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").addInput("concentration");
    model.component("comp1").material("mat1").propertyGroup("ElectrodePotential").addInput("temperature");
    model.component("comp1").material("mat1").propertyGroup("OperationalSOC")
         .label("Operational electrode state-of-charge");
    model.component("comp1").material("mat1").propertyGroup("OperationalSOC").set("socmax", "1");
    model.component("comp1").material("mat1").propertyGroup("OperationalSOC").set("socmin", "0");
    model.component("comp1").material("mat1").propertyGroup("ic").label("Intercalation strain");
    model.component("comp1").material("mat1").propertyGroup("ic").func("int1").label("Interpolation 1");
    model.component("comp1").material("mat1").propertyGroup("ic").func("int1").set("funcname", "dVOLdSOL");
    model.component("comp1").material("mat1").propertyGroup("ic").func("int1")
         .set("table", new String[][]{{"0", "0"}, 
         {"0.006802721088435382", "0.12500000000000178"}, 
         {"0.06316812439261421", "1.2736486486486491"}, 
         {"0.11175898931000966", "2.523648648648649"}, 
         {"0.17978620019436342", "3.5709459459459474"}, 
         {"0.2400388726919339", "4.449324324324325"}, 
         {"0.2905733722060252", "5.192567567567568"}, 
         {"0.3566569484936831", "5.66554054054054"}, 
         {"0.4188532555879494", "5.969594594594595"}, 
         {"0.48104956268221566", "6.10472972972973"}, 
         {"0.5432458697764819", "6.173648648648647"}, 
         {"0.58600583090379", "6.306081081081081"}, 
         {"0.6112730806608356", "7.726351351351352"}, 
         {"0.6443148688046647", "8.570945945945946"}, 
         {"0.694849368318756", "9.449324324324323"}, 
         {"0.7414965986394557", "10.29391891891892"}, 
         {"0.7764820213799805", "10.902027027027025"}, 
         {"0.8231292517006802", "11.543918918918918"}, 
         {"0.8542274052478133", "12.152027027027026"}, 
         {"0.8833819241982507", "12.827702702702702"}, 
         {"0.9183673469387755", "12.996621621621621"}, 
         {"0.9494655004859086", "13.16554054054054"}});
    model.component("comp1").material("mat1").propertyGroup("ic").func("int1").set("extrap", "linear");
    model.component("comp1").material("mat1").propertyGroup("ic").func("int1").set("fununit", new String[]{"%"});
    model.component("comp1").material("mat1").propertyGroup("ic").func("int1").set("argunit", new String[]{"1"});
    model.component("comp1").material("mat1").propertyGroup("ic").set("dvol", "dVOLdSOL(c/elpot.cEeqref)");

    return model;
  }

  public static Model run4(Model model) {
    model.component("comp1").material("mat1").propertyGroup("ic")
         .setPropertyInfo("dvol", "S. Schweidler, L. de Biasi, A. Schiele, P. Hartmann, T. Brezesinski and J. Janek, \"Volume Changes of Graphite Anodes Revisited: A Combined Operando X-Ray Diffraction and In Situ Pressure Analysis Study\", J. Phys. Chem. C, 2018, 122, 8829\u20138835");
    model.component("comp1").material("mat1").propertyGroup("ic").addInput("concentration");
    model.component("comp1").material("mat1").propertyGroup("ElectrolyteConductivity")
         .set("sigmal", new String[]{"4.453", "0", "0", "0", "4.453", "0", "0", "0", "4.453"});
    model.component("comp1").material("mat1").materialType("nonSolid");
    model.component("comp1").material("mat2").label("LiPF6 in 3:7 EC:EMC (Liquid, Li-ion Battery)");
    model.component("comp1").material("mat2").propertyGroup("def").label("Basic");
    model.component("comp1").material("mat2").propertyGroup("def").func("int1").label("Interpolation 1");
    model.component("comp1").material("mat2").propertyGroup("def").func("int1").set("funcname", "DL_int1");
    model.component("comp1").material("mat2").propertyGroup("def").func("int1")
         .set("table", new String[][]{{"200", "3.9e-10/(1-200*59e-6)"}, 
         {"500", "4.12e-10/(1-500*59e-6)"}, 
         {"800", "4e-10/(1-800*59e-6)"}, 
         {"1000", "3.8e-10/(1-1000*59e-6)"}, 
         {"1200", "3.50e-10/(1-1200*59e-6)"}, 
         {"1600", "2.68e-10/(1-1600*59e-6)"}, 
         {"2000", "1.9e-10/(1-2000*59e-6)"}});
    model.component("comp1").material("mat2").propertyGroup("def").func("int1").set("interp", "piecewisecubic");
    model.component("comp1").material("mat2").propertyGroup("def").func("int1")
         .set("fununit", new String[]{"m^2/s"});
    model.component("comp1").material("mat2").propertyGroup("def").func("int1").set("argunit", new String[]{""});
    model.component("comp1").material("mat2").propertyGroup("def")
         .set("diffusion", new String[]{"DL_int1(c/1[mol/m^3])*exp(16500/8.314*(1/(T_ref/1[K])-1/(T2/1[K])))", "0", "0", "0", "DL_int1(c/1[mol/m^3])*exp(16500/8.314*(1/(T_ref/1[K])-1/(T2/1[K])))", "0", "0", "0", "DL_int1(c/1[mol/m^3])*exp(16500/8.314*(1/(T_ref/1[K])-1/(T2/1[K])))"});
    model.component("comp1").material("mat2").propertyGroup("def")
         .setPropertyInfo("diffusion", "T. G. Zavalis, M. Behm, and G. Lindbergh, \"Investigations of Short-Circuit Scenarios in a Lithium-Ion Battery Cell,\" J. Electrochem. Soc., vol. 159, p. A848, 2012.");
    model.component("comp1").material("mat2").propertyGroup("def").set("T_ref", "298[K]");
    model.component("comp1").material("mat2").propertyGroup("def").descr("T_ref", "");
    model.component("comp1").material("mat2").propertyGroup("def").set("T2", "min(393.15,max(T,223.15))");
    model.component("comp1").material("mat2").propertyGroup("def").descr("T2", "");
    model.component("comp1").material("mat2").propertyGroup("def").addInput("concentration");
    model.component("comp1").material("mat2").propertyGroup("def").addInput("temperature");
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteConductivity")
         .label("Electrolyte conductivity");
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteConductivity").func("int1")
         .label("Interpolation 1");
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteConductivity").func("int1")
         .set("funcname", "sigmal_int1");
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteConductivity").func("int1")
         .set("table", new String[][]{{"0", "1e-6"}, 
         {"200", "0.455"}, 
         {"500", "0.783"}, 
         {"800", "0.935"}, 
         {"1000", "0.95"}, 
         {"1200", "0.927"}, 
         {"1600", "0.78"}, 
         {"2000", "0.60"}, 
         {"2200", "0.515"}});
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteConductivity").func("int1")
         .set("interp", "piecewisecubic");
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteConductivity").func("int1")
         .set("fununit", new String[]{"S/m"});
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteConductivity").func("int1")
         .set("argunit", new String[]{""});
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteConductivity").func("int2")
         .label("\u7535\u89e3\u6db2\u7535\u5bfc\u7387-25\u2103\u6d77\u4eff");
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteConductivity").func("int2")
         .set("funcname", "sigmal_int2");
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteConductivity").func("int2")
         .set("table", new String[][]{{"700", "8.86911"}, 
         {"800", "8.786777"}, 
         {"900", "8.84274"}, 
         {"1000", "8.765095"}, 
         {"1100", "8.454808"}, 
         {"1200", "8.444846"}});
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteConductivity").func("int2")
         .set("interp", "piecewisecubic");
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteConductivity").func("int2")
         .set("fununit", new String[]{"mS/cm"});
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteConductivity")
         .set("sigmal", new String[]{"sigmal_int1(c/1[mol/m^3])*exp(4000/8.314*(1/(T_ref2/1[K])-1/(T3/1[K])))", "0", "0", "0", "sigmal_int1(c/1[mol/m^3])*exp(4000/8.314*(1/(T_ref2/1[K])-1/(T3/1[K])))", "0", "0", "0", "sigmal_int1(c/1[mol/m^3])*exp(4000/8.314*(1/(T_ref2/1[K])-1/(T3/1[K])))"});
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteConductivity")
         .setPropertyInfo("sigmal", "T. G. Zavalis, M. Behm, and G. Lindbergh, \"Investigations of Short-Circuit Scenarios in a Lithium-Ion Battery Cell,\" J. Electrochem. Soc., vol. 159, p. A848, 2012.");
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteConductivity").set("T_ref2", "298[K]");
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteConductivity").descr("T_ref2", "");
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteConductivity")
         .set("T3", "min(393.15,max(T,223.15))");
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteConductivity").descr("T3", "");
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteConductivity").addInput("concentration");
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteConductivity").addInput("temperature");
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties").label("Species properties");
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties").func("int1")
         .label("Interpolation 1");
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties").func("int1")
         .set("funcname", "transpNm_int1");
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties").func("int1")
         .set("table", new String[][]{{"200", "0.37"}, 
         {"500", "0.322"}, 
         {"800", "0.27"}, 
         {"1000", "0.251"}, 
         {"1200", "0.248"}, 
         {"1600", "0.236"}, 
         {"2000", "0.11"}});
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties").func("int1")
         .set("interp", "piecewisecubic");
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties").func("int1")
         .set("fununit", new String[]{""});
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties").func("int1")
         .set("argunit", new String[]{""});
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties").func("int2")
         .label("Interpolation 2");
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties").func("int2")
         .set("funcname", "actdep_int1");
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties").func("int2")
         .set("table", new String[][]{{"200", "0"}, 
         {"500", "0.29"}, 
         {"800", "0.695"}, 
         {"1000", "1"}, 
         {"1200", "1.32"}, 
         {"1600", "2.07"}, 
         {"2000", "2.50"}});
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties").func("int2")
         .set("interp", "piecewisecubic");
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties").func("int2")
         .set("fununit", new String[]{""});
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties").func("int2")
         .set("argunit", new String[]{""});
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties")
         .set("transpNum", "transpNm_int1(c/1[mol/m^3])");
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties")
         .setPropertyInfo("transpNum", "A. Nyman, M. Behm, and G. Lindbergh, \u201cElectrochemical characterisation and modelling of the mass transport phenomena in LiPF6-EC-EMC,\u201d Electrochim. Acta, vol. 53, p. 6356, 2008.");
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties")
         .set("fcl", "actdep_int1(c/1[mol/m^3])*exp(-1000/8.314*(1/(T_ref3/1[K])-1/(T4/1[K])))");
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties")
         .setPropertyInfo("fcl", "T. G. Zavalis, M. Behm, and G. Lindbergh, \"Investigations of Short-Circuit Scenarios in a Lithium-Ion Battery Cell,\" J. Electrochem. Soc., vol. 159, p. A848, 2012.");
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties")
         .set("T4", "min(393.15,max(T,223.15))");
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties").descr("T4", "");
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties").set("T_ref3", "298[K]");
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties").descr("T_ref3", "");
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties").addInput("concentration");
    model.component("comp1").material("mat2").propertyGroup("SpeciesProperties").addInput("temperature");
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteSaltConcentration")
         .label("Electrolyte salt concentration");
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteSaltConcentration").identifier("cElsalt");
    model.component("comp1").material("mat2").propertyGroup("ElectrolyteSaltConcentration")
         .set("cElsalt", "1000[mol/m^3]");
    model.component("comp1").material("mat3").label("LFP, LiFePO4 (Positive, Li-ion Battery)");
    model.component("comp1").material("mat3").propertyGroup("def").label("Basic");
    model.component("comp1").material("mat3").propertyGroup("def").set("poissonsratio", "");
    model.component("comp1").material("mat3").propertyGroup("def").set("youngsmodulus", "");
    model.component("comp1").material("mat3").propertyGroup("def").set("poissonsratio", "0.3");
    model.component("comp1").material("mat3").propertyGroup("def")
         .setPropertyInfo("poissonsratio", "T. Maxisch and G. Ceder, Elastic properties of olivine LixFePO4 from first principles, Physical Review B 73, 174112, 2006\r\n");
    model.component("comp1").material("mat3").propertyGroup("def").set("youngsmodulus", "117.8[GPa]");
    model.component("comp1").material("mat3").propertyGroup("def")
         .setPropertyInfo("youngsmodulus", "T. Maxisch and G. Ceder, Elastic properties of olivine LixFePO4 from first principles, Physical Review B 73, 174112, 2006");
    model.component("comp1").material("mat3").propertyGroup("def")
         .set("diffusion", new String[]{"3e-13[m^2/s]*k_dp", "0", "0", "0", "3e-13[m^2/s]*k_dp", "0", "0", "0", "3e-13[m^2/s]*k_dp"});
    model.component("comp1").material("mat3").propertyGroup("def")
         .setPropertyInfo("diffusion", "U. S. Kasavajjula, C. Wang, and P. E. Arce, \"Discharge Model for LiFePO4 Accounting for the Solid Solution Range\", J. Electrochemical Soc., vol. 155, p. A866, 2008");
    model.component("comp1").material("mat3").propertyGroup("def")
         .set("electricconductivity", new String[]{"sigma_pos", "0", "0", "0", "sigma_pos", "0", "0", "0", "sigma_pos"});
    model.component("comp1").material("mat3").propertyGroup("def")
         .setPropertyInfo("electricconductivity", "U. S. Kasavajjula, C. Wang, and P. E. Arce, \"Discharge Model for LiFePO4 Accounting for the Solid Solution Range\", J. Electrochemical Soc., vol. 155, p. A866, 2008");
    model.component("comp1").material("mat3").propertyGroup("def")
         .set("thermalconductivity", new String[]{"1[W/(m*K)]", "0", "0", "0", "1[W/(m*K)]", "0", "0", "0", "1[W/(m*K)]"});
    model.component("comp1").material("mat3").propertyGroup("def")
         .setPropertyInfo("thermalconductivity", "R. E. Gerver and J. P. Meyers, \"Three-Dimensional Modeling of Electrochemical Performance and Heat Generation of Lithium-Ion Betteries in Tabbed Planar Configurations\", J. Electrochemical Soc., vol. 158, p. A835, 2011");
    model.component("comp1").material("mat3").propertyGroup("def").set("heatcapacity", "881[J/(kg*K)]");
    model.component("comp1").material("mat3").propertyGroup("def")
         .setPropertyInfo("heatcapacity", "R. E. Gerver and J. P. Meyers, \"Three-Dimensional Modeling of Electrochemical Performance and Heat Generation of Lithium-Ion Betteries in Tabbed Planar Configurations\", J. Electrochemical Soc., vol. 158, p. A835, 2011");
    model.component("comp1").material("mat3").propertyGroup("def").set("density", "3600[kg/m^3]");
    model.component("comp1").material("mat3").propertyGroup("def")
         .setPropertyInfo("density", "N. Nitta, F. Wu, J. Tae Lee, and G. Yushin, Materials Today, Volume 18, Number 5, June 2015");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").label("Equilibrium potential");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int7")
         .label("Interpolation 1.1");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int7")
         .set("funcname", "Eeq_int1");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int7")
         .set("table", new String[][]{{"0.01", "3.538446291"}, 
         {"0.02", "3.430533"}, 
         {"0.03", "3.424694609"}, 
         {"0.04", "3.424504348"}, 
         {"0.05", "3.424500072"}, 
         {"0.06", "3.424500001"}, 
         {"0.07", "3.4245"}, 
         {"0.08", "3.4245"}, 
         {"0.09", "3.4245"}, 
         {"0.1", "3.4245"}, 
         {"0.11", "3.4245"}, 
         {"0.12", "3.4245"}, 
         {"0.13", "3.4245"}, 
         {"0.14", "3.4245"}, 
         {"0.15", "3.4245"}, 
         {"0.16", "3.4245"}, 
         {"0.17", "3.4245"}, 
         {"0.18", "3.4245"}, 
         {"0.19", "3.4245"}, 
         {"0.2", "3.4245"}, 
         {"0.21", "3.4245"}, 
         {"0.22", "3.4245"}, 
         {"0.23", "3.4245"}, 
         {"0.24", "3.4245"}, 
         {"0.25", "3.4245"}, 
         {"0.26", "3.4245"}, 
         {"0.27", "3.4245"}, 
         {"0.28", "3.4245"}, 
         {"0.29", "3.4245"}, 
         {"0.3", "3.4245"}, 
         {"0.31", "3.4245"}, 
         {"0.32", "3.4245"}, 
         {"0.33", "3.4245"}, 
         {"0.34", "3.4245"}, 
         {"0.35", "3.4245"}, 
         {"0.36", "3.4245"}, 
         {"0.37", "3.4245"}, 
         {"0.38", "3.4245"}, 
         {"0.39", "3.4245"}, 
         {"0.4", "3.4245"}, 
         {"0.41", "3.4245"}, 
         {"0.42", "3.4245"}, 
         {"0.43", "3.4245"}, 
         {"0.44", "3.4245"}, 
         {"0.45", "3.4245"}, 
         {"0.46", "3.4245"}, 
         {"0.47", "3.4245"}, 
         {"0.48", "3.4245"}, 
         {"0.49", "3.4245"}, 
         {"0.5", "3.4245"}, 
         {"0.51", "3.4245"}, 
         {"0.52", "3.4245"}, 
         {"0.53", "3.4245"}, 
         {"0.54", "3.4245"}, 
         {"0.55", "3.4245"}, 
         {"0.56", "3.4245"}, 
         {"0.57", "3.4245"}, 
         {"0.58", "3.4245"}, 
         {"0.59", "3.4245"}, 
         {"0.6", "3.4245"}, 
         {"0.61", "3.4245"}, 
         {"0.62", "3.4245"}, 
         {"0.63", "3.4245"}, 
         {"0.64", "3.4245"}, 
         {"0.65", "3.4245"}, 
         {"0.66", "3.4245"}, 
         {"0.67", "3.4245"}, 
         {"0.68", "3.4245"}, 
         {"0.69", "3.4245"}, 
         {"0.7", "3.4245"}, 
         {"0.71", "3.4245"}, 
         {"0.72", "3.4245"}, 
         {"0.73", "3.4245"}, 
         {"0.74", "3.4245"}, 
         {"0.75", "3.4245"}, 
         {"0.76", "3.4245"}, 
         {"0.77", "3.4245"}, 
         {"0.78", "3.4245"}, 
         {"0.79", "3.4245"}, 
         {"0.8", "3.424499996"}, 
         {"0.81", "3.424499875"}, 
         {"0.82", "3.424497592"}, 
         {"0.83", "3.424471778"}, 
         {"0.84", "3.424279811"}, 
         {"0.85", "3.423272375"}, 
         {"0.86", "3.419316956"}, 
         {"0.87", "3.407123221"}, 
         {"0.88", "3.376401149"}, 
         {"0.89", "3.311000755"}, 
         {"0.9", "3.190071347"}});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int7")
         .set("interp", "piecewisecubic");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int7")
         .set("extrap", "linear");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int7")
         .set("fununit", new String[]{"V"});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int7")
         .set("argunit", new String[]{""});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int1")
         .label("Interpolation 1");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int1")
         .set("funcname", "Eeq_int2323");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int1")
         .set("table", new String[][]{{"0.015", "3.538446291"}, 
         {"0.02", "3.430533"}, 
         {"0.03", "3.424694609"}, 
         {"0.04", "3.424504348"}, 
         {"0.05", "3.424500072"}, 
         {"0.06", "3.424500001"}, 
         {"0.07", "3.4245"}, 
         {"0.08", "3.4245"}, 
         {"0.09", "3.4245"}, 
         {"0.1", "3.4245"}, 
         {"0.11", "3.4245"}, 
         {"0.12", "3.4245"}, 
         {"0.13", "3.4245"}, 
         {"0.14", "3.4245"}, 
         {"0.15", "3.4245"}, 
         {"0.16", "3.4245"}, 
         {"0.17", "3.4245"}, 
         {"0.18", "3.4245"}, 
         {"0.19", "3.4245"}, 
         {"0.2", "3.4245"}, 
         {"0.21", "3.4245"}, 
         {"0.22", "3.4245"}, 
         {"0.23", "3.4245"}, 
         {"0.24", "3.4245"}, 
         {"0.25", "3.4245"}, 
         {"0.26", "3.4245"}, 
         {"0.27", "3.4245"}, 
         {"0.28", "3.4245"}, 
         {"0.29", "3.4245"}, 
         {"0.3", "3.4245"}, 
         {"0.31", "3.4245"}, 
         {"0.32", "3.4245"}, 
         {"0.33", "3.4245"}, 
         {"0.34", "3.4245"}, 
         {"0.35", "3.4245"}, 
         {"0.36", "3.4245"}, 
         {"0.37", "3.4245"}, 
         {"0.38", "3.4245"}, 
         {"0.39", "3.4245"}, 
         {"0.4", "3.4245"}, 
         {"0.41", "3.4245"}, 
         {"0.42", "3.4245"}, 
         {"0.43", "3.4245"}, 
         {"0.44", "3.4245"}, 
         {"0.45", "3.4245"}, 
         {"0.46", "3.4245"}, 
         {"0.47", "3.4245"}, 
         {"0.48", "3.4245"}, 
         {"0.49", "3.4245"}, 
         {"0.5", "3.4245"}, 
         {"0.51", "3.4245"}, 
         {"0.52", "3.4245"}, 
         {"0.53", "3.4245"}, 
         {"0.54", "3.4245"}, 
         {"0.55", "3.4245"}, 
         {"0.56", "3.4245"}, 
         {"0.57", "3.4245"}, 
         {"0.58", "3.4245"}, 
         {"0.59", "3.4245"}, 
         {"0.6", "3.4245"}, 
         {"0.61", "3.4245"}, 
         {"0.62", "3.4245"}, 
         {"0.63", "3.4245"}, 
         {"0.64", "3.4245"}, 
         {"0.65", "3.4245"}, 
         {"0.66", "3.4245"}, 
         {"0.67", "3.4245"}, 
         {"0.68", "3.4245"}, 
         {"0.69", "3.4245"}, 
         {"0.7", "3.4245"}, 
         {"0.71", "3.4245"}, 
         {"0.72", "3.4245"}, 
         {"0.73", "3.4245"}, 
         {"0.74", "3.4245"}, 
         {"0.75", "3.4245"}, 
         {"0.76", "3.4245"}, 
         {"0.77", "3.4245"}, 
         {"0.78", "3.4245"}, 
         {"0.79", "3.4245"}, 
         {"0.8", "3.424499996"}, 
         {"0.81", "3.424499875"}, 
         {"0.82", "3.424497592"}, 
         {"0.83", "3.424471778"}, 
         {"0.84", "3.424279811"}, 
         {"0.85", "3.423272375"}, 
         {"0.86", "3.419316956"}, 
         {"0.87", "3.407123221"}, 
         {"0.88", "3.376401149"}, 
         {"0.89", "3.311000755"}, 
         {"0.9", "3.190071347"}});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int1")
         .set("interp", "piecewisecubic");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int1")
         .set("extrap", "linear");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int1")
         .set("fununit", new String[]{"V"});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int1")
         .set("argunit", new String[]{""});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int2")
         .label("Interpolation 2");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int2")
         .set("funcname", "dEeqdT_int1");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int2")
         .set("table", new String[][]{{"0.01", "8.62369E-06"}, 
         {"0.02", "2.8778E-05"}, 
         {"0.03", "4.26811E-05"}, 
         {"0.04", "5.15442E-05"}, 
         {"0.05", "5.64049E-05"}, 
         {"0.06", "5.81456E-05"}, 
         {"0.07", "5.75106E-05"}, 
         {"0.08", "5.51215E-05"}, 
         {"0.09", "5.14917E-05"}, 
         {"0.1", "4.704E-05"}, 
         {"0.11", "4.2102E-05"}, 
         {"0.12", "3.69419E-05"}, 
         {"0.13", "3.17622E-05"}, 
         {"0.14", "2.6713E-05"}, 
         {"0.15", "2.19002E-05"}, 
         {"0.16", "1.73927E-05"}, 
         {"0.17", "1.32297E-05"}, 
         {"0.18", "9.42567E-06"}, 
         {"0.19", "5.97636E-06"}, 
         {"0.2", "2.86293E-06"}, 
         {"0.21", "5.60889E-08"}, 
         {"0.22", "-2.48057E-06"}, 
         {"0.23", "-4.78758E-06"}, 
         {"0.24", "-6.90723E-06"}, 
         {"0.25", "-8.88151E-06"}, 
         {"0.26", "-1.07505E-05"}, 
         {"0.27", "-1.25511E-05"}, 
         {"0.28", "-1.43163E-05"}, 
         {"0.29", "-1.60739E-05"}, 
         {"0.3", "-1.7847E-05"}, 
         {"0.31", "-1.9653E-05"}, 
         {"0.32", "-2.15043E-05"}, 
         {"0.33", "-2.3408E-05"}, 
         {"0.34", "-2.53663E-05"}, 
         {"0.35", "-2.73772E-05"}, 
         {"0.36", "-2.94348E-05"}, 
         {"0.37", "-3.153E-05"}, 
         {"0.38", "-3.36509E-05"}, 
         {"0.39", "-3.57841E-05"}, 
         {"0.4", "-3.79145E-05"}, 
         {"0.41", "-4.00267E-05"}, 
         {"0.42", "-4.21054E-05"}, 
         {"0.43", "-4.41359E-05"}, 
         {"0.44", "-4.61049E-05"}, 
         {"0.45", "-4.8001E-05"}, 
         {"0.46", "-4.98148E-05"}, 
         {"0.47", "-5.15398E-05"}, 
         {"0.48", "-5.31723E-05"}, 
         {"0.49", "-5.47118E-05"}, 
         {"0.5", "-5.6161E-05"}, 
         {"0.51", "-5.75258E-05"}, 
         {"0.52", "-5.88155E-05"}, 
         {"0.53", "-6.00423E-05"}, 
         {"0.54", "-6.12209E-05"}, 
         {"0.55", "-6.2369E-05"}, 
         {"0.56", "-6.35057E-05"}, 
         {"0.57", "-6.46519E-05"}, 
         {"0.58", "-6.58293E-05"}, 
         {"0.59", "-6.70598E-05"}, 
         {"0.6", "-6.83648E-05"}, 
         {"0.61", "-6.97648E-05"}, 
         {"0.62", "-7.12781E-05"}, 
         {"0.63", "-7.29204E-05"}, 
         {"0.64", "-7.47038E-05"}, 
         {"0.65", "-7.66365E-05"}, 
         {"0.66", "-7.87216E-05"}, 
         {"0.67", "-8.09567E-05"}, 
         {"0.68", "-8.33335E-05"}, 
         {"0.69", "-8.58371E-05"}, 
         {"0.7", "-8.84457E-05"}, 
         {"0.71", "-9.11307E-05"}, 
         {"0.72", "-9.38568E-05"}, 
         {"0.73", "-9.65818E-05"}, 
         {"0.74", "-9.92574E-05"}, 
         {"0.75", "-0.00010183"}, 
         {"0.76", "-0.000104242"}, 
         {"0.77", "-0.000106433"}, 
         {"0.78", "-0.000108342"}, 
         {"0.79", "-0.000109907"}, 
         {"0.8", "-0.000111074"}, 
         {"0.81", "-0.000111793"}, 
         {"0.82", "-0.000112027"}, 
         {"0.83", "-0.000111752"}, 
         {"0.84", "-0.000110967"}, 
         {"0.85", "-0.000109694"}, 
         {"0.86", "-0.000107991"}, 
         {"0.87", "-0.000105953"}, 
         {"0.88", "-0.000103722"}, 
         {"0.89", "-0.000101498"}, 
         {"0.9", "-9.95453E-05"}});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int2")
         .set("fununit", new String[]{"V/K"});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int2")
         .set("argunit", new String[]{""});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int3")
         .set("funcname", "Eeq_int222");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int3")
         .set("table", new String[][]{{"0.0005", "3.5231"}, 
         {"0.001", "3.5082"}, 
         {"0.0015", "3.4981"}, 
         {"0.002", "3.4897"}, 
         {"0.0025", "3.4823"}, 
         {"0.003", "3.4758"}, 
         {"0.0035", "3.4705"}, 
         {"0.004", "3.4649"}, 
         {"0.0045", "3.46"}, 
         {"0.005", "3.4553"}, 
         {"0.0055", "3.4511"}, 
         {"0.006", "3.4471"}, 
         {"0.0065", "3.4434"}, 
         {"0.007", "3.4398"}, 
         {"0.0075", "3.4366"}, 
         {"0.008", "3.4335"}, 
         {"0.0085", "3.4308"}, 
         {"0.009", "3.428"}, 
         {"0.0095", "3.4257"}, 
         {"0.01", "3.4234"}, 
         {"0.01125", "3.4184"}, 
         {"0.01275", "3.4139"}, 
         {"0.014", "3.411"}, 
         {"0.018", "3.4049"}, 
         {"0.0245", "3.4014"}, 
         {"0.03", "3.4001"}, 
         {"0.04", "3.3995"}, 
         {"0.05", "3.3991"}, 
         {"0.06", "3.3989"}, 
         {"0.07025", "3.3987"}, 
         {"0.13025", "3.3975"}, 
         {"0.19625", "3.3961"}, 
         {"0.21775", "3.3955"}, 
         {"0.29125", "3.3938"}, 
         {"0.35375", "3.3925"}, 
         {"0.39625", "3.3912"}, 
         {"0.45525", "3.3896"}, 
         {"0.56275", "3.3862"}, 
         {"0.58025", "3.3846"}, 
         {"0.58875", "3.3839"}, 
         {"0.64775", "3.3809"}, 
         {"0.68525", "3.3775"}, 
         {"0.71775", "3.3744"}, 
         {"0.73625", "3.3722"}, 
         {"0.73775", "3.3721"}, 
         {"0.76775", "3.3698"}, 
         {"0.79525", "3.364"}, 
         {"0.79625", "3.3637"}, 
         {"0.80275", "3.3623"}, 
         {"0.81875", "3.3583"}, 
         {"0.82275", "3.3574"}, 
         {"0.82375", "3.357"}, 
         {"0.82525", "3.3564"}, 
         {"0.82775", "3.3558"}, 
         {"0.83275", "3.3543"}, 
         {"0.84875", "3.349"}, 
         {"0.85025", "3.3485"}, 
         {"0.85125", "3.3481"}, 
         {"0.85275", "3.3474"}, 
         {"0.85525", "3.3465"}, 
         {"0.85625", "3.3459"}, 
         {"0.85775", "3.3453"}, 
         {"0.87375", "3.338"}, 
         {"0.87525", "3.3375"}, 
         {"0.87625", "3.3371"}, 
         {"0.87775", "3.3366"}, 
         {"0.87875", "3.3363"}, 
         {"0.88025", "3.3355"}, 
         {"0.88125", "3.335"}, 
         {"0.88275", "3.3344"}, 
         {"0.89875", "3.3262"}, 
         {"0.90025", "3.3254"}, 
         {"0.90125", "3.3247"}, 
         {"0.90275", "3.3239"}, 
         {"0.90375", "3.3233"}, 
         {"0.90525", "3.3223"}, 
         {"0.92525", "3.304"}, 
         {"0.92625", "3.3028"}, 
         {"0.92775", "3.3009"}, 
         {"0.92875", "3.2999"}, 
         {"0.93025", "3.2983"}, 
         {"0.94625", "3.271"}, 
         {"0.94775", "3.2656"}, 
         {"0.94875", "3.2617"}, 
         {"0.95025", "3.2554"}, 
         {"0.95125", "3.2506"}, 
         {"0.95275", "3.2416"}, 
         {"0.95375", "3.2352"}, 
         {"0.95525", "3.2244"}, 
         {"0.95625", "3.2158"}, 
         {"0.95775", "3.2014"}, 
         {"0.95875", "3.1907"}, 
         {"0.96025", "3.1727"}, 
         {"0.96125", "3.16"}, 
         {"0.96275", "3.1411"}, 
         {"0.96375", "3.1267"}, 
         {"0.96525", "3.1045"}, 
         {"0.96625", "3.089"}, 
         {"0.96775", "3.0649"}, 
         {"0.96875", "3.0486"}, 
         {"0.97025", "3.023"}, 
         {"0.97125", "3.0053"}, 
         {"0.97275", "2.9781"}, 
         {"0.97375", "2.9594"}, 
         {"0.97525", "2.9302"}, 
         {"0.97625", "2.9098"}, 
         {"0.97775", "2.8785"}, 
         {"0.97875", "2.8573"}, 
         {"0.98025", "2.8238"}, 
         {"0.98125", "2.8009"}, 
         {"0.98275", "2.7654"}, 
         {"0.98375", "2.7406"}, 
         {"0.98525", "2.7014"}, 
         {"0.98625", "2.6739"}, 
         {"0.98775", "2.6302"}, 
         {"0.98875", "2.5998"}, 
         {"0.99025", "2.5501"}, 
         {"0.99125", "2.514"}, 
         {"0.99275", "2.4538"}, 
         {"0.99375", "2.4079"}, 
         {"0.99525", "2.3312"}, 
         {"0.99625", "2.2743"}, 
         {"0.99775", "2.1861"}, 
         {"0.99875", "2.1261"}});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int3")
         .set("interp", "piecewisecubic");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int3")
         .set("extrap", "linear");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int3")
         .set("fununit", new String[]{""});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int5")
         .set("funcname", "Eeq_int5");

    return model;
  }

  public static Model run5(Model model) {
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int5")
         .set("table", loadTableFromSnapshot("run5", "int5"));

    return model;
  }
  public static Model run6(Model model) {
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int5")
         .set("interp", "piecewisecubic");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int5")
         .set("extrap", "linear");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int5")
         .set("fununit", new String[]{""});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int6")
         .set("funcname", "Eeq_int6");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int6")
         .set("table", new String[][]{{"0.015", "3.5384"}, 
         {"0.01522", "3.52634"}, 
         {"0.01552", "3.51428"}, 
         {"0.01602", "3.50223"}, 
         {"0.01673", "3.49019"}, 
         {"0.01755", "3.47816"}, 
         {"0.01857", "3.46614"}, 
         {"0.01984", "3.45415"}, 
         {"0.02131", "3.44218"}, 
         {"0.02321", "3.43027"}, 
         {"0.02583", "3.41851"}, 
         {"0.03048", "3.40748"}, 
         {"0.03976", "3.40101"}, 
         {"0.05151", "3.39956"}, 
         {"0.06308", "3.39917"}, 
         {"0.07483", "3.39907"}, 
         {"0.08603", "3.39865"}, 
         {"0.09778", "3.39873"}, 
         {"0.10923", "3.3989"}, 
         {"0.1207", "3.39837"}, 
         {"0.1325", "3.39798"}, 
         {"0.14418", "3.39746"}, 
         {"0.15544", "3.39773"}, 
         {"0.16683", "3.39769"}, 
         {"0.1784", "3.39699"}, 
         {"0.18991", "3.39667"}, 
         {"0.2013", "3.3963"}, 
         {"0.21281", "3.39603"}, 
         {"0.22419", "3.39557"}, 
         {"0.23569", "3.39524"}, 
         {"0.24745", "3.3953"}, 
         {"0.2589", "3.3954"}, 
         {"0.27031", "3.3949"}, 
         {"0.28163", "3.39451"}, 
         {"0.29325", "3.39386"}, 
         {"0.30485", "3.39392"}, 
         {"0.31592", "3.39411"}, 
         {"0.32712", "3.39387"}, 
         {"0.33858", "3.39348"}, 
         {"0.35", "3.39314"}, 
         {"0.36149", "3.39257"}, 
         {"0.37326", "3.39216"}, 
         {"0.3848", "3.39183"}, 
         {"0.39677", "3.39134"}, 
         {"0.40812", "3.3911"}, 
         {"0.41916", "3.39123"}, 
         {"0.43056", "3.39141"}, 
         {"0.4419", "3.39078"}, 
         {"0.45353", "3.39011"}, 
         {"0.46503", "3.38935"}, 
         {"0.47688", "3.38962"}, 
         {"0.48839", "3.38964"}, 
         {"0.49966", "3.38902"}, 
         {"0.51138", "3.38833"}, 
         {"0.52271", "3.38757"}, 
         {"0.53375", "3.38697"}, 
         {"0.5456", "3.38624"}, 
         {"0.55697", "3.38675"}, 
         {"0.56827", "3.38623"}, 
         {"0.57983", "3.38513"}, 
         {"0.59134", "3.38402"}, 
         {"0.60271", "3.38321"}, 
         {"0.61447", "3.38369"}, 
         {"0.62615", "3.38297"}, 
         {"0.63775", "3.38218"}, 
         {"0.64905", "3.38112"}, 
         {"0.66069", "3.38013"}, 
         {"0.67204", "3.37917"}, 
         {"0.68334", "3.37808"}, 
         {"0.69468", "3.377"}, 
         {"0.70629", "3.37601"}, 
         {"0.7177", "3.37465"}, 
         {"0.72921", "3.37357"}, 
         {"0.74039", "3.37213"}, 
         {"0.75185", "3.3716"}, 
         {"0.76366", "3.37087"}, 
         {"0.77497", "3.36889"}, 
         {"0.78638", "3.36659"}, 
         {"0.79791", "3.36393"}, 
         {"0.80941", "3.36114"}, 
         {"0.82091", "3.35831"}, 
         {"0.83214", "3.35514"}, 
         {"0.84354", "3.35142"}, 
         {"0.85401", "3.34756"}, 
         {"0.86491", "3.34273"}, 
         {"0.87574", "3.33774"}, 
         {"0.88651", "3.33307"}, 
         {"0.89721", "3.32774"}, 
         {"0.90722", "3.32131"}, 
         {"0.91635", "3.31388"}, 
         {"0.92441", "3.30526"}, 
         {"0.93222", "3.29635"}, 
         {"0.93944", "3.28695"}, 
         {"0.94459", "3.27615"}, 
         {"0.94793", "3.26458"}, 
         {"0.95066", "3.25284"}, 
         {"0.95271", "3.24096"}, 
         {"0.95445", "3.22903"}, 
         {"0.95592", "3.21706"}, 
         {"0.95719", "3.20507"}, 
         {"0.95832", "3.19306"}, 
         {"0.95935", "3.18105"}, 
         {"0.96029", "3.16902"}, 
         {"0.96122", "3.157"}, 
         {"0.96215", "3.14497"}, 
         {"0.96301", "3.13294"}, 
         {"0.96386", "3.12091"}, 
         {"0.96465", "3.10887"}, 
         {"0.96538", "3.09684"}, 
         {"0.96617", "3.0848"}, 
         {"0.96689", "3.07276"}, 
         {"0.96765", "3.06072"}, 
         {"0.96834", "3.04868"}, 
         {"0.96907", "3.03664"}, 
         {"0.96975", "3.0246"}, 
         {"0.97043", "3.01256"}, 
         {"0.97112", "3.00052"}, 
         {"0.97175", "2.98847"}, 
         {"0.9724", "2.97643"}, 
         {"0.97304", "2.96438"}, 
         {"0.97366", "2.95234"}, 
         {"0.97426", "2.94029"}, 
         {"0.97487", "2.92825"}, 
         {"0.97542", "2.9162"}, 
         {"0.976", "2.90415"}, 
         {"0.97657", "2.8921"}, 
         {"0.97715", "2.88005"}, 
         {"0.97773", "2.86801"}, 
         {"0.97827", "2.85596"}, 
         {"0.97879", "2.84391"}, 
         {"0.97932", "2.83186"}, 
         {"0.97984", "2.81981"}, 
         {"0.98036", "2.80776"}, 
         {"0.98086", "2.79571"}, 
         {"0.98137", "2.78366"}, 
         {"0.98186", "2.77161"}, 
         {"0.98236", "2.75955"}, 
         {"0.98284", "2.7475"}, 
         {"0.98331", "2.73545"}, 
         {"0.98378", "2.7234"}, 
         {"0.98425", "2.71135"}, 
         {"0.9847", "2.69929"}, 
         {"0.98515", "2.68724"}, 
         {"0.98557", "2.67519"}, 
         {"0.98598", "2.66313"}, 
         {"0.98638", "2.65108"}, 
         {"0.98679", "2.63902"}, 
         {"0.9872", "2.62697"}, 
         {"0.98759", "2.61491"}, 
         {"0.98793", "2.60285"}, 
         {"0.98831", "2.5908"}, 
         {"0.98867", "2.57874"}, 
         {"0.98901", "2.56669"}, 
         {"0.98937", "2.55463"}, 
         {"0.98972", "2.54257"}, 
         {"0.99004", "2.53052"}, 
         {"0.99038", "2.51846"}, 
         {"0.9907", "2.5064"}, 
         {"0.991", "2.49434"}, 
         {"0.99132", "2.48229"}, 
         {"0.9916", "2.47023"}, 
         {"0.99188", "2.45817"}, 
         {"0.99217", "2.44611"}, 
         {"0.99241", "2.43405"}, 
         {"0.9927", "2.42199"}, 
         {"0.99292", "2.40993"}, 
         {"0.99319", "2.39788"}, 
         {"0.9934", "2.38582"}, 
         {"0.99366", "2.37376"}, 
         {"0.99387", "2.3617"}, 
         {"0.9941", "2.34964"}, 
         {"0.99433", "2.33758"}, 
         {"0.99454", "2.32552"}, 
         {"0.99477", "2.31346"}, 
         {"0.99496", "2.3014"}, 
         {"0.99519", "2.28934"}, 
         {"0.99537", "2.27728"}, 
         {"0.99559", "2.26522"}, 
         {"0.99579", "2.25316"}, 
         {"0.99599", "2.2411"}, 
         {"0.99621", "2.22904"}, 
         {"0.99639", "2.21698"}, 
         {"0.9966", "2.20492"}, 
         {"0.9968", "2.19286"}, 
         {"0.99699", "2.1808"}, 
         {"0.99721", "2.16874"}, 
         {"0.99739", "2.15668"}, 
         {"0.9976", "2.14462"}, 
         {"0.99779", "2.13256"}, 
         {"0.99799", "2.1205"}, 
         {"0.99819", "2.10844"}, 
         {"0.99837", "2.09638"}, 
         {"0.99859", "2.08432"}, 
         {"0.99878", "2.07226"}, 
         {"0.99898", "2.0602"}, 
         {"0.9992", "2.04814"}, 
         {"0.99938", "2.03608"}, 
         {"0.9996", "2.02402"}, 
         {"0.99979", "2.01196"}, 
         {"1", "1.9999"}, 
         {"", ""}});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int6")
         .set("interp", "piecewisecubic");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int6")
         .set("extrap", "linear");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int6")
         .set("fununit", new String[]{"V"});

    return model;
  }

  public static Model run7(Model model) {
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int8")
         .set("table", loadTableFromSnapshot("run7", "int8"));

    return model;
  }
  public static Model run8(Model model) {
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int8")
         .set("interp", "piecewisecubic");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int8")
         .set("extrap", "linear");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int8")
         .set("fununit", new String[]{"V"});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int10")
         .label("1218-LFPOCV -0.01-0.95");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int10")
         .set("funcname", "Eeq_int101");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int10")
         .set("table", new String[][]{{"0.01", "3.6518"}, 
         {"0.01472", "3.45283"}, 
         {"0.01945", "3.43918"}, 
         {"0.02417", "3.43962"}, 
         {"0.02889", "3.4406"}, 
         {"0.03362", "3.4413"}, 
         {"0.03834", "3.44161"}, 
         {"0.04307", "3.44175"}, 
         {"0.04779", "3.442"}, 
         {"0.05251", "3.4419"}, 
         {"0.05724", "3.4418"}, 
         {"0.06196", "3.4417"}, 
         {"0.06668", "3.4417"}, 
         {"0.07141", "3.4416"}, 
         {"0.07613", "3.4414"}, 
         {"0.08085", "3.4416"}, 
         {"0.08558", "3.44146"}, 
         {"0.0903", "3.44144"}, 
         {"0.09503", "3.44143"}, 
         {"0.09975", "3.4413"}, 
         {"0.10447", "3.4411"}, 
         {"0.1092", "3.44139"}, 
         {"0.11392", "3.44126"}, 
         {"0.11864", "3.4413"}, 
         {"0.12337", "3.4411"}, 
         {"0.12809", "3.44137"}, 
         {"0.13281", "3.44134"}, 
         {"0.13754", "3.44137"}, 
         {"0.14226", "3.44116"}, 
         {"0.14698", "3.44121"}, 
         {"0.15171", "3.4411"}, 
         {"0.15643", "3.44113"}, 
         {"0.16116", "3.44116"}, 
         {"0.16588", "3.44097"}, 
         {"0.1706", "3.4411"}, 
         {"0.17533", "3.44113"}, 
         {"0.18005", "3.44123"}, 
         {"0.18477", "3.4413"}, 
         {"0.1895", "3.4411"}, 
         {"0.19422", "3.44111"}, 
         {"0.19894", "3.44129"}, 
         {"0.20367", "3.4411"}, 
         {"0.20839", "3.4411"}, 
         {"0.21312", "3.4411"}, 
         {"0.21784", "3.4409"}, 
         {"0.22256", "3.44107"}, 
         {"0.22729", "3.4413"}, 
         {"0.23201", "3.44115"}, 
         {"0.23673", "3.4411"}, 
         {"0.24146", "3.44107"}, 
         {"0.24618", "3.4409"}, 
         {"0.2509", "3.44097"}, 
         {"0.25563", "3.4409"}, 
         {"0.26035", "3.44101"}, 
         {"0.26508", "3.4411"}, 
         {"0.2698", "3.44097"}, 
         {"0.27452", "3.4409"}, 
         {"0.27925", "3.44087"}, 
         {"0.28397", "3.4409"}, 
         {"0.28869", "3.4408"}, 
         {"0.29342", "3.44079"}, 
         {"0.29814", "3.44064"}, 
         {"0.30286", "3.44081"}, 
         {"0.30759", "3.44061"}, 
         {"0.31231", "3.44079"}, 
         {"0.31704", "3.4406"}, 
         {"0.32176", "3.4406"}, 
         {"0.32648", "3.44058"}, 
         {"0.33121", "3.4405"}, 
         {"0.33593", "3.44054"}, 
         {"0.34065", "3.4405"}, 
         {"0.34538", "3.44038"}, 
         {"0.3501", "3.44042"}, 
         {"0.35482", "3.4402"}, 
         {"0.35955", "3.4402"}, 
         {"0.36427", "3.4402"}, 
         {"0.36899", "3.44013"}, 
         {"0.37372", "3.43996"}, 
         {"0.37844", "3.44"}, 
         {"0.38317", "3.44"}, 
         {"0.38789", "3.4397"}, 
         {"0.39261", "3.4399"}, 
         {"0.39734", "3.43961"}, 
         {"0.40206", "3.4397"}, 
         {"0.40678", "3.43969"}, 
         {"0.41151", "3.43957"}, 
         {"0.41623", "3.43935"}, 
         {"0.42095", "3.4394"}, 
         {"0.42568", "3.4392"}, 
         {"0.4304", "3.43937"}, 
         {"0.43513", "3.4392"}, 
         {"0.43985", "3.4391"}, 
         {"0.44457", "3.4391"}, 
         {"0.4493", "3.43914"}, 
         {"0.45402", "3.43914"}, 
         {"0.45874", "3.43897"}, 
         {"0.46347", "3.43882"}, 
         {"0.46819", "3.43887"}, 
         {"0.47291", "3.4389"}, 
         {"0.47764", "3.43867"}, 
         {"0.48236", "3.43852"}, 
         {"0.48709", "3.4386"}, 
         {"0.49181", "3.4385"}, 
         {"0.49653", "3.4383"}, 
         {"0.50126", "3.4385"}, 
         {"0.50598", "3.4386"}, 
         {"0.5107", "3.43852"}, 
         {"0.51543", "3.4383"}, 
         {"0.52015", "3.4382"}, 
         {"0.52487", "3.4382"}, 
         {"0.5296", "3.438"}, 
         {"0.53432", "3.43785"}, 
         {"0.53905", "3.4378"}, 
         {"0.54377", "3.43774"}, 
         {"0.54849", "3.43774"}, 
         {"0.55322", "3.4378"}, 
         {"0.55794", "3.4377"}, 
         {"0.56266", "3.4375"}, 
         {"0.56739", "3.43759"}, 
         {"0.57211", "3.43746"}, 
         {"0.57683", "3.43725"}, 
         {"0.58156", "3.43736"}, 
         {"0.58628", "3.43711"}, 
         {"0.59101", "3.4371"}, 
         {"0.59573", "3.4371"}, 
         {"0.60045", "3.43707"}, 
         {"0.60518", "3.4369"}, 
         {"0.6099", "3.4368"}, 
         {"0.61462", "3.4368"}, 
         {"0.61935", "3.4366"}, 
         {"0.62407", "3.43657"}, 
         {"0.62879", "3.43653"}, 
         {"0.63352", "3.43637"}, 
         {"0.63824", "3.4365"}, 
         {"0.64296", "3.4363"}, 
         {"0.64769", "3.4361"}, 
         {"0.65241", "3.436"}, 
         {"0.65714", "3.436"}, 
         {"0.66186", "3.43588"}, 
         {"0.66658", "3.4357"}, 
         {"0.67131", "3.43572"}, 
         {"0.67603", "3.4355"}, 
         {"0.68075", "3.4355"}, 
         {"0.68548", "3.43539"}, 
         {"0.6902", "3.4352"}, 
         {"0.69492", "3.43506"}, 
         {"0.69965", "3.4349"}, 
         {"0.70437", "3.4344"}, 
         {"0.7091", "3.43441"}, 
         {"0.71382", "3.4343"}, 
         {"0.71854", "3.4343"}, 
         {"0.72327", "3.43416"}, 
         {"0.72799", "3.43392"}, 
         {"0.73271", "3.4335"}, 
         {"0.73744", "3.43346"}, 
         {"0.74216", "3.43333"}, 
         {"0.74688", "3.4329"}, 
         {"0.75161", "3.4327"}, 
         {"0.75633", "3.43251"}, 
         {"0.76106", "3.43222"}, 
         {"0.76578", "3.43185"}, 
         {"0.7705", "3.43133"}, 
         {"0.77523", "3.43088"}, 
         {"0.77995", "3.4304"}, 
         {"0.78467", "3.42995"}, 
         {"0.7894", "3.42933"}, 
         {"0.79412", "3.4285"}, 
         {"0.79884", "3.4276"}, 
         {"0.80357", "3.4265"}, 
         {"0.80829", "3.42526"}, 
         {"0.81302", "3.42314"}, 
         {"0.81774", "3.42056"}, 
         {"0.82246", "3.41761"}, 
         {"0.82719", "3.41377"}, 
         {"0.83191", "3.41028"}, 
         {"0.83663", "3.40693"}, 
         {"0.84136", "3.4044"}, 
         {"0.84608", "3.40165"}, 
         {"0.8508", "3.39964"}, 
         {"0.85553", "3.39813"}, 
         {"0.86025", "3.39645"}, 
         {"0.86497", "3.39446"}, 
         {"0.8697", "3.39272"}, 
         {"0.87442", "3.39096"}, 
         {"0.87915", "3.38907"}, 
         {"0.88387", "3.38738"}, 
         {"0.88859", "3.38557"}, 
         {"0.89332", "3.3831"}, 
         {"0.89804", "3.37939"}, 
         {"0.90276", "3.37515"}, 
         {"0.90749", "3.3685"}, 
         {"0.91221", "3.3588"}, 
         {"0.91693", "3.34224"}, 
         {"0.92166", "3.31462"}, 
         {"0.92638", "3.2705"}, 
         {"0.93111", "3.19297"}, 
         {"0.93583", "3.05811"}, 
         {"0.94055", "2.86856"}, 
         {"0.94528", "2.54882"}, 
         {"0.95", "2.0359"}});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int10")
         .set("interp", "piecewisecubic");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int10")
         .set("extrap", "linear");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int10")
         .set("fununit", new String[]{"V"});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int10")
         .set("argunit", new String[]{"1"});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int11")
         .label("OCV-LFP-0.01-1");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int11")
         .set("funcname", "Eeq_int10");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int11")
         .set("table", new String[][]{{"0.01", "3.63829"}, 
         {"0.01472", "3.43932"}, 
         {"0.01945", "3.42949"}, 
         {"0.02417", "3.42849"}, 
         {"0.02889", "3.42849"}, 
         {"0.03362", "3.42849"}, 
         {"0.03834", "3.42849"}, 
         {"0.04307", "3.42849"}, 
         {"0.04779", "3.42849"}, 
         {"0.05251", "3.42839"}, 
         {"0.05724", "3.42829"}, 
         {"0.06196", "3.42819"}, 
         {"0.06668", "3.42819"}, 
         {"0.07141", "3.42809"}, 
         {"0.07613", "3.42789"}, 
         {"0.08085", "3.42809"}, 
         {"0.08558", "3.42796"}, 
         {"0.0903", "3.42794"}, 
         {"0.09503", "3.42792"}, 
         {"0.09975", "3.42779"}, 
         {"0.10447", "3.42759"}, 
         {"0.1092", "3.42788"}, 
         {"0.11392", "3.42775"}, 
         {"0.11864", "3.42779"}, 
         {"0.12337", "3.42759"}, 
         {"0.12809", "3.42786"}, 
         {"0.13281", "3.42784"}, 
         {"0.13754", "3.42786"}, 
         {"0.14226", "3.42766"}, 
         {"0.14698", "3.4277"}, 
         {"0.15171", "3.42759"}, 
         {"0.15643", "3.42763"}, 
         {"0.16116", "3.42765"}, 
         {"0.16588", "3.42746"}, 
         {"0.1706", "3.4276"}, 
         {"0.17533", "3.42763"}, 
         {"0.18005", "3.42773"}, 
         {"0.18477", "3.42779"}, 
         {"0.1895", "3.42759"}, 
         {"0.19422", "3.4276"}, 
         {"0.19894", "3.42779"}, 
         {"0.20367", "3.42759"}, 
         {"0.20839", "3.42759"}, 
         {"0.21312", "3.42759"}, 
         {"0.21784", "3.42739"}, 
         {"0.22256", "3.42757"}, 
         {"0.22729", "3.42779"}, 
         {"0.23201", "3.42764"}, 
         {"0.23673", "3.42759"}, 
         {"0.24146", "3.42756"}, 
         {"0.24618", "3.42739"}, 
         {"0.2509", "3.42747"}, 
         {"0.25563", "3.42739"}, 
         {"0.26035", "3.4275"}, 
         {"0.26508", "3.42759"}, 
         {"0.2698", "3.42747"}, 
         {"0.27452", "3.42739"}, 
         {"0.27925", "3.42737"}, 
         {"0.28397", "3.42739"}, 
         {"0.28869", "3.42729"}, 
         {"0.29342", "3.42728"}, 
         {"0.29814", "3.42713"}, 
         {"0.30286", "3.4273"}, 
         {"0.30759", "3.4271"}, 
         {"0.31231", "3.42728"}, 
         {"0.31704", "3.42709"}, 
         {"0.32176", "3.42709"}, 
         {"0.32648", "3.42707"}, 
         {"0.33121", "3.42699"}, 
         {"0.33593", "3.42703"}, 
         {"0.34065", "3.42699"}, 
         {"0.34538", "3.42687"}, 
         {"0.3501", "3.42692"}, 
         {"0.35482", "3.42669"}, 
         {"0.35955", "3.42669"}, 
         {"0.36427", "3.42669"}, 
         {"0.36899", "3.42663"}, 
         {"0.37372", "3.42646"}, 
         {"0.37844", "3.42649"}, 
         {"0.38317", "3.42649"}, 
         {"0.38789", "3.42619"}, 
         {"0.39261", "3.42639"}, 
         {"0.39734", "3.4261"}, 
         {"0.40206", "3.42619"}, 
         {"0.40678", "3.42619"}, 
         {"0.41151", "3.42607"}, 
         {"0.41623", "3.42585"}, 
         {"0.42095", "3.42589"}, 
         {"0.42568", "3.42569"}, 
         {"0.4304", "3.42587"}, 
         {"0.43513", "3.42569"}, 
         {"0.43985", "3.42559"}, 
         {"0.44457", "3.42559"}, 
         {"0.4493", "3.42564"}, 
         {"0.45402", "3.42564"}, 
         {"0.45874", "3.42547"}, 
         {"0.46347", "3.42532"}, 
         {"0.46819", "3.42537"}, 
         {"0.47291", "3.42539"}, 
         {"0.47764", "3.42517"}, 
         {"0.48236", "3.42502"}, 
         {"0.48709", "3.42509"}, 
         {"0.49181", "3.42499"}, 
         {"0.49653", "3.4248"}, 
         {"0.50126", "3.42499"}, 
         {"0.50598", "3.42509"}, 
         {"0.5107", "3.42501"}, 
         {"0.51543", "3.42479"}, 
         {"0.52015", "3.42469"}, 
         {"0.52487", "3.42469"}, 
         {"0.5296", "3.42449"}, 
         {"0.53432", "3.42435"}, 
         {"0.53905", "3.42429"}, 
         {"0.54377", "3.42424"}, 
         {"0.54849", "3.42424"}, 
         {"0.55322", "3.42429"}, 
         {"0.55794", "3.42419"}, 
         {"0.56266", "3.42399"}, 
         {"0.56739", "3.42408"}, 
         {"0.57211", "3.42395"}, 
         {"0.57683", "3.42375"}, 
         {"0.58156", "3.42385"}, 
         {"0.58628", "3.4236"}, 
         {"0.59101", "3.42359"}, 
         {"0.59573", "3.42359"}, 
         {"0.60045", "3.42356"}, 
         {"0.60518", "3.42339"}, 
         {"0.6099", "3.42329"}, 
         {"0.61462", "3.42329"}, 
         {"0.61935", "3.42309"}, 
         {"0.62407", "3.42307"}, 
         {"0.62879", "3.42302"}, 
         {"0.63352", "3.42287"}, 
         {"0.63824", "3.42299"}, 
         {"0.64296", "3.42279"}, 
         {"0.64769", "3.42259"}, 
         {"0.65241", "3.42249"}, 
         {"0.65714", "3.42249"}, 
         {"0.66186", "3.42238"}, 
         {"0.66658", "3.42219"}, 
         {"0.67131", "3.42222"}, 
         {"0.67603", "3.42199"}, 
         {"0.68075", "3.42199"}, 
         {"0.68548", "3.42189"}, 
         {"0.6902", "3.42169"}, 
         {"0.69492", "3.42155"}, 
         {"0.69965", "3.42139"}, 
         {"0.70437", "3.42089"}, 
         {"0.7091", "3.4209"}, 
         {"0.71382", "3.42079"}, 
         {"0.71854", "3.42079"}, 
         {"0.72327", "3.42065"}, 
         {"0.72799", "3.42041"}, 
         {"0.73271", "3.41999"}, 
         {"0.73744", "3.41996"}, 
         {"0.74216", "3.41983"}, 
         {"0.74688", "3.41939"}, 
         {"0.75161", "3.41919"}, 
         {"0.75633", "3.419"}, 
         {"0.76106", "3.41872"}, 
         {"0.76578", "3.41834"}, 
         {"0.7705", "3.41783"}, 
         {"0.77523", "3.41737"}, 
         {"0.77995", "3.41689"}, 
         {"0.78467", "3.41644"}, 
         {"0.7894", "3.41583"}, 
         {"0.79412", "3.41499"}, 
         {"0.79884", "3.41409"}, 
         {"0.80357", "3.41299"}, 
         {"0.80829", "3.41176"}, 
         {"0.81302", "3.40964"}, 
         {"0.81774", "3.40706"}, 
         {"0.82246", "3.40411"}, 
         {"0.82719", "3.40027"}, 
         {"0.83191", "3.39677"}, 
         {"0.83663", "3.39343"}, 
         {"0.84136", "3.39089"}, 
         {"0.84608", "3.38814"}, 
         {"0.8508", "3.38613"}, 
         {"0.85553", "3.38462"}, 
         {"0.86025", "3.38294"}, 
         {"0.86497", "3.38096"}, 
         {"0.8697", "3.37922"}, 
         {"0.87442", "3.37746"}, 
         {"0.87915", "3.37557"}, 
         {"0.88387", "3.37388"}, 
         {"0.88859", "3.37206"}, 
         {"0.89332", "3.36959"}, 
         {"0.89804", "3.36588"}, 
         {"0.90276", "3.36164"}, 
         {"0.90749", "3.35499"}, 
         {"0.91221", "3.34529"}, 
         {"0.91693", "3.32873"}, 
         {"0.92166", "3.30111"}, 
         {"0.92638", "3.257"}, 
         {"0.93111", "3.17947"}, 
         {"0.93583", "3.0446"}, 
         {"0.94055", "2.85505"}, 
         {"0.94528", "2.53531"}, 
         {"0.95", "2.02239"}});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int11")
         .set("interp", "piecewisecubic");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int11")
         .set("extrap", "linear");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int11")
         .set("fununit", new String[]{"V"});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int11")
         .set("argunit", new String[]{"1"});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int12")
         .label("OCV-LFP-0.01-0.95 - \u526f\u672c 1");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int12")
         .set("funcname", "Eeq_int12");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int12")
         .set("table", new String[][]{{"0.01", "3.63829"}, 
         {"0.01472", "3.43932"}, 
         {"0.01945", "3.42567"}, 
         {"0.02417", "3.42612"}, 
         {"0.02889", "3.42709"}, 
         {"0.03362", "3.4278"}, 
         {"0.03834", "3.42811"}, 
         {"0.04307", "3.42824"}, 
         {"0.04779", "3.42849"}, 
         {"0.05251", "3.42839"}, 
         {"0.05724", "3.42829"}, 
         {"0.06196", "3.42819"}, 
         {"0.06668", "3.42819"}, 
         {"0.07141", "3.42809"}, 
         {"0.07613", "3.42789"}, 
         {"0.08085", "3.42809"}, 
         {"0.08558", "3.42796"}, 
         {"0.0903", "3.42794"}, 
         {"0.09503", "3.42792"}, 
         {"0.09975", "3.42779"}, 
         {"0.10447", "3.42759"}, 
         {"0.1092", "3.42788"}, 
         {"0.11392", "3.42775"}, 
         {"0.11864", "3.42779"}, 
         {"0.12337", "3.42759"}, 
         {"0.12809", "3.42786"}, 
         {"0.13281", "3.42784"}, 
         {"0.13754", "3.42786"}, 
         {"0.14226", "3.42766"}, 
         {"0.14698", "3.4277"}, 
         {"0.15171", "3.42759"}, 
         {"0.15643", "3.42763"}, 
         {"0.16116", "3.42765"}, 
         {"0.16588", "3.42746"}, 
         {"0.1706", "3.4276"}, 
         {"0.17533", "3.42763"}, 
         {"0.18005", "3.42773"}, 
         {"0.18477", "3.42779"}, 
         {"0.1895", "3.42759"}, 
         {"0.19422", "3.4276"}, 
         {"0.19894", "3.42779"}, 
         {"0.20367", "3.42759"}, 
         {"0.20839", "3.42759"}, 
         {"0.21312", "3.42759"}, 
         {"0.21784", "3.42739"}, 
         {"0.22256", "3.42757"}, 
         {"0.22729", "3.42779"}, 
         {"0.23201", "3.42764"}, 
         {"0.23673", "3.42759"}, 
         {"0.24146", "3.42756"}, 
         {"0.24618", "3.42739"}, 
         {"0.2509", "3.42747"}, 
         {"0.25563", "3.42739"}, 
         {"0.26035", "3.4275"}, 
         {"0.26508", "3.42759"}, 
         {"0.2698", "3.42747"}, 
         {"0.27452", "3.42739"}, 
         {"0.27925", "3.42737"}, 
         {"0.28397", "3.42739"}, 
         {"0.28869", "3.42729"}, 
         {"0.29342", "3.42728"}, 
         {"0.29814", "3.42713"}, 
         {"0.30286", "3.4273"}, 
         {"0.30759", "3.4271"}, 
         {"0.31231", "3.42728"}, 
         {"0.31704", "3.42709"}, 
         {"0.32176", "3.42709"}, 
         {"0.32648", "3.42707"}, 
         {"0.33121", "3.42699"}, 
         {"0.33593", "3.42703"}, 
         {"0.34065", "3.42699"}, 
         {"0.34538", "3.42687"}, 
         {"0.3501", "3.42692"}, 
         {"0.35482", "3.42669"}, 
         {"0.35955", "3.42669"}, 
         {"0.36427", "3.42669"}, 
         {"0.36899", "3.42663"}, 
         {"0.37372", "3.42646"}, 
         {"0.37844", "3.42649"}, 
         {"0.38317", "3.42649"}, 
         {"0.38789", "3.42619"}, 
         {"0.39261", "3.42639"}, 
         {"0.39734", "3.4261"}, 
         {"0.40206", "3.42619"}, 
         {"0.40678", "3.42619"}, 
         {"0.41151", "3.42607"}, 
         {"0.41623", "3.42585"}, 
         {"0.42095", "3.42589"}, 
         {"0.42568", "3.42569"}, 
         {"0.4304", "3.42587"}, 
         {"0.43513", "3.42569"}, 
         {"0.43985", "3.42559"}, 
         {"0.44457", "3.42559"}, 
         {"0.4493", "3.42564"}, 
         {"0.45402", "3.42564"}, 
         {"0.45874", "3.42547"}, 
         {"0.46347", "3.42532"}, 
         {"0.46819", "3.42537"}, 
         {"0.47291", "3.42539"}, 
         {"0.47764", "3.42517"}, 
         {"0.48236", "3.42502"}, 
         {"0.48709", "3.42509"}, 
         {"0.49181", "3.42499"}, 
         {"0.49653", "3.4248"}, 
         {"0.50126", "3.42499"}, 
         {"0.50598", "3.42509"}, 
         {"0.5107", "3.42501"}, 
         {"0.51543", "3.42479"}, 
         {"0.52015", "3.42469"}, 
         {"0.52487", "3.42469"}, 
         {"0.5296", "3.42449"}, 
         {"0.53432", "3.42435"}, 
         {"0.53905", "3.42429"}, 
         {"0.54377", "3.42424"}, 
         {"0.54849", "3.42424"}, 
         {"0.55322", "3.42429"}, 
         {"0.55794", "3.42419"}, 
         {"0.56266", "3.42399"}, 
         {"0.56739", "3.42408"}, 
         {"0.57211", "3.42395"}, 
         {"0.57683", "3.42375"}, 
         {"0.58156", "3.42385"}, 
         {"0.58628", "3.4236"}, 
         {"0.59101", "3.42359"}, 
         {"0.59573", "3.42359"}, 
         {"0.60045", "3.42356"}, 
         {"0.60518", "3.42339"}, 
         {"0.6099", "3.42329"}, 
         {"0.61462", "3.42329"}, 
         {"0.61935", "3.42309"}, 
         {"0.62407", "3.42307"}, 
         {"0.62879", "3.42302"}, 
         {"0.63352", "3.42287"}, 
         {"0.63824", "3.42299"}, 
         {"0.64296", "3.42279"}, 
         {"0.64769", "3.42259"}, 
         {"0.65241", "3.42249"}, 
         {"0.65714", "3.42249"}, 
         {"0.66186", "3.42238"}, 
         {"0.66658", "3.42219"}, 
         {"0.67131", "3.42222"}, 
         {"0.67603", "3.42199"}, 
         {"0.68075", "3.42199"}, 
         {"0.68548", "3.42189"}, 
         {"0.6902", "3.42169"}, 
         {"0.69492", "3.42155"}, 
         {"0.69965", "3.42139"}, 
         {"0.70437", "3.42089"}, 
         {"0.7091", "3.4209"}, 
         {"0.71382", "3.42079"}, 
         {"0.71854", "3.42079"}, 
         {"0.72327", "3.42065"}, 
         {"0.72799", "3.42041"}, 
         {"0.73271", "3.41999"}, 
         {"0.73744", "3.41996"}, 
         {"0.74216", "3.41983"}, 
         {"0.74688", "3.41939"}, 
         {"0.75161", "3.41919"}, 
         {"0.75633", "3.419"}, 
         {"0.76106", "3.41872"}, 
         {"0.76578", "3.41834"}, 
         {"0.7705", "3.41783"}, 
         {"0.77523", "3.41737"}, 
         {"0.77995", "3.41689"}, 
         {"0.78467", "3.41644"}, 
         {"0.7894", "3.41583"}, 
         {"0.79412", "3.41499"}, 
         {"0.79884", "3.41409"}, 
         {"0.80357", "3.41299"}, 
         {"0.80829", "3.41176"}, 
         {"0.81302", "3.40964"}, 
         {"0.81774", "3.40706"}, 
         {"0.82246", "3.40411"}, 
         {"0.82719", "3.40027"}, 
         {"0.83191", "3.39677"}, 
         {"0.83663", "3.39343"}, 
         {"0.84136", "3.39089"}, 
         {"0.84608", "3.38814"}, 
         {"0.8508", "3.38613"}, 
         {"0.85553", "3.38462"}, 
         {"0.86025", "3.38294"}, 
         {"0.86497", "3.38096"}, 
         {"0.8697", "3.37922"}, 
         {"0.87442", "3.37746"}, 
         {"0.87915", "3.37557"}, 
         {"0.88387", "3.37388"}, 
         {"0.88859", "3.37206"}, 
         {"0.89332", "3.36959"}, 
         {"0.89804", "3.36588"}, 
         {"0.90276", "3.36164"}, 
         {"0.90749", "3.35499"}, 
         {"0.91221", "3.34529"}, 
         {"0.91693", "3.32873"}, 
         {"0.92166", "3.30111"}, 
         {"0.92638", "3.257"}, 
         {"0.93111", "3.17947"}, 
         {"0.93583", "3.0446"}, 
         {"0.94055", "2.85505"}, 
         {"0.94528", "2.53531"}, 
         {"0.95", "2.02239"}});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int12")
         .set("interp", "piecewisecubic");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int12")
         .set("extrap", "linear");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int12")
         .set("fununit", new String[]{"V"});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int12")
         .set("argunit", new String[]{"1"});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int13")
         .label("OCV-LFP-0.01-0.95 - \u526f\u672c 2");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int13")
         .set("funcname", "Eeq_int13");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int13")
         .set("table", new String[][]{{"0.01", "3.63829"}, 
         {"0.01472", "3.43932"}, 
         {"0.01945", "3.42949"}, 
         {"0.02417", "3.42849"}, 
         {"0.02889", "3.42849"}, 
         {"0.03362", "3.42849"}, 
         {"0.03834", "3.42849"}, 
         {"0.04307", "3.42849"}, 
         {"0.04779", "3.42849"}, 
         {"0.05251", "3.42839"}, 
         {"0.05724", "3.42829"}, 
         {"0.06196", "3.42819"}, 
         {"0.06668", "3.42819"}, 
         {"0.07141", "3.42809"}, 
         {"0.07613", "3.42789"}, 
         {"0.08085", "3.42809"}, 
         {"0.08558", "3.42796"}, 
         {"0.0903", "3.42794"}, 
         {"0.09503", "3.42792"}, 
         {"0.09975", "3.42779"}, 
         {"0.10447", "3.42759"}, 
         {"0.1092", "3.42788"}, 
         {"0.11392", "3.42775"}, 
         {"0.11864", "3.42779"}, 
         {"0.12337", "3.42759"}, 
         {"0.12809", "3.42786"}, 
         {"0.13281", "3.42784"}, 
         {"0.13754", "3.42786"}, 
         {"0.14226", "3.42766"}, 
         {"0.14698", "3.4277"}, 
         {"0.15171", "3.42759"}, 
         {"0.15643", "3.42763"}, 
         {"0.16116", "3.42765"}, 
         {"0.16588", "3.42746"}, 
         {"0.1706", "3.4276"}, 
         {"0.17533", "3.42763"}, 
         {"0.18005", "3.42773"}, 
         {"0.18477", "3.42779"}, 
         {"0.1895", "3.42759"}, 
         {"0.19422", "3.4276"}, 
         {"0.19894", "3.42779"}, 
         {"0.20367", "3.42759"}, 
         {"0.20839", "3.42759"}, 
         {"0.21312", "3.42759"}, 
         {"0.21784", "3.42739"}, 
         {"0.22256", "3.42757"}, 
         {"0.22729", "3.42779"}, 
         {"0.23201", "3.42764"}, 
         {"0.23673", "3.42759"}, 
         {"0.24146", "3.42756"}, 
         {"0.24618", "3.42739"}, 
         {"0.2509", "3.42747"}, 
         {"0.25563", "3.42739"}, 
         {"0.26035", "3.4275"}, 
         {"0.26508", "3.42759"}, 
         {"0.2698", "3.42747"}, 
         {"0.27452", "3.42739"}, 
         {"0.27925", "3.42737"}, 
         {"0.28397", "3.42739"}, 
         {"0.28869", "3.42729"}, 
         {"0.29342", "3.42728"}, 
         {"0.29814", "3.42713"}, 
         {"0.30286", "3.4273"}, 
         {"0.30759", "3.4271"}, 
         {"0.31231", "3.42728"}, 
         {"0.31704", "3.42709"}, 
         {"0.32176", "3.42709"}, 
         {"0.32648", "3.42707"}, 
         {"0.33121", "3.42699"}, 
         {"0.33593", "3.42703"}, 
         {"0.34065", "3.42699"}, 
         {"0.34538", "3.42687"}, 
         {"0.3501", "3.42692"}, 
         {"0.35482", "3.42669"}, 
         {"0.35955", "3.42669"}, 
         {"0.36427", "3.42669"}, 
         {"0.36899", "3.42663"}, 
         {"0.37372", "3.42646"}, 
         {"0.37844", "3.42649"}, 
         {"0.38317", "3.42649"}, 
         {"0.38789", "3.42619"}, 
         {"0.39261", "3.42639"}, 
         {"0.39734", "3.4261"}, 
         {"0.40206", "3.42619"}, 
         {"0.40678", "3.42619"}, 
         {"0.41151", "3.42607"}, 
         {"0.41623", "3.42585"}, 
         {"0.42095", "3.42589"}, 
         {"0.42568", "3.42569"}, 
         {"0.4304", "3.42587"}, 
         {"0.43513", "3.42569"}, 
         {"0.43985", "3.42559"}, 
         {"0.44457", "3.42559"}, 
         {"0.4493", "3.42564"}, 
         {"0.45402", "3.42564"}, 
         {"0.45874", "3.42547"}, 
         {"0.46347", "3.42532"}, 
         {"0.46819", "3.42537"}, 
         {"0.47291", "3.42539"}, 
         {"0.47764", "3.42517"}, 
         {"0.48236", "3.42502"}, 
         {"0.48709", "3.42509"}, 
         {"0.49181", "3.42499"}, 
         {"0.49653", "3.4248"}, 
         {"0.50126", "3.42499"}, 
         {"0.50598", "3.42509"}, 
         {"0.5107", "3.42501"}, 
         {"0.51543", "3.42479"}, 
         {"0.52015", "3.42469"}, 
         {"0.52487", "3.42469"}, 
         {"0.5296", "3.42449"}, 
         {"0.53432", "3.42435"}, 
         {"0.53905", "3.42429"}, 
         {"0.54377", "3.42424"}, 
         {"0.54849", "3.42424"}, 
         {"0.55322", "3.42429"}, 
         {"0.55794", "3.42419"}, 
         {"0.56266", "3.42399"}, 
         {"0.56739", "3.42408"}, 
         {"0.57211", "3.42395"}, 
         {"0.57683", "3.42375"}, 
         {"0.58156", "3.42385"}, 
         {"0.58628", "3.4236"}, 
         {"0.59101", "3.42359"}, 
         {"0.59573", "3.42359"}, 
         {"0.60045", "3.42356"}, 
         {"0.60518", "3.42339"}, 
         {"0.6099", "3.42329"}, 
         {"0.61462", "3.42329"}, 
         {"0.61935", "3.42309"}, 
         {"0.62407", "3.42307"}, 
         {"0.62879", "3.42302"}, 
         {"0.63352", "3.42287"}, 
         {"0.63824", "3.42299"}, 
         {"0.64296", "3.42279"}, 
         {"0.64769", "3.42259"}, 
         {"0.65241", "3.42249"}, 
         {"0.65714", "3.42249"}, 
         {"0.66186", "3.42238"}, 
         {"0.66658", "3.42219"}, 
         {"0.67131", "3.42222"}, 
         {"0.67603", "3.42199"}, 
         {"0.68075", "3.42199"}, 
         {"0.68548", "3.42189"}, 
         {"0.6902", "3.42169"}, 
         {"0.69492", "3.42155"}, 
         {"0.69965", "3.42139"}, 
         {"0.70437", "3.42089"}, 
         {"0.7091", "3.4209"}, 
         {"0.71382", "3.42079"}, 
         {"0.71854", "3.42079"}, 
         {"0.72327", "3.42065"}, 
         {"0.72799", "3.42041"}, 
         {"0.73271", "3.41999"}, 
         {"0.73744", "3.41996"}, 
         {"0.74216", "3.41983"}, 
         {"0.74688", "3.41939"}, 
         {"0.75161", "3.41919"}, 
         {"0.75633", "3.419"}, 
         {"0.76106", "3.41872"}, 
         {"0.76578", "3.41834"}, 
         {"0.7705", "3.41783"}, 
         {"0.77523", "3.41737"}, 
         {"0.77995", "3.41689"}, 
         {"0.78467", "3.41644"}, 
         {"0.7894", "3.41583"}, 
         {"0.79412", "3.41499"}, 
         {"0.79884", "3.41409"}, 
         {"0.80357", "3.41299"}, 
         {"0.80829", "3.41176"}, 
         {"0.81302", "3.40964"}, 
         {"0.81774", "3.40706"}, 
         {"0.82246", "3.40411"}, 
         {"0.82719", "3.40027"}, 
         {"0.83191", "3.39677"}, 
         {"0.83663", "3.39343"}, 
         {"0.84136", "3.39089"}, 
         {"0.84608", "3.38814"}, 
         {"0.8508", "3.38613"}, 
         {"0.85553", "3.38462"}, 
         {"0.86025", "3.38294"}, 
         {"0.86497", "3.38096"}, 
         {"0.8697", "3.37922"}, 
         {"0.87442", "3.37746"}, 
         {"0.87915", "3.37557"}, 
         {"0.88387", "3.37388"}, 
         {"0.88859", "3.37206"}, 
         {"0.89332", "3.36959"}, 
         {"0.89804", "3.36588"}, 
         {"0.90276", "3.36164"}, 
         {"0.90749", "3.35499"}, 
         {"0.91221", "3.34529"}, 
         {"0.91693", "3.32873"}, 
         {"0.92166", "3.30111"}, 
         {"0.92638", "3.257"}, 
         {"0.93111", "3.17947"}, 
         {"0.93583", "3.0446"}, 
         {"0.94055", "2.85505"}, 
         {"0.94528", "2.53531"}, 
         {"0.95", "2.02239"}});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int13")
         .set("interp", "piecewisecubic");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int13")
         .set("extrap", "linear");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int13")
         .set("fununit", new String[]{"V"});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int13")
         .set("argunit", new String[]{"1"});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int14")
         .label("OCV-LFP-0.01-1.1");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int14")
         .set("funcname", "Eeq_int14");

    return model;
  }

  public static Model run9(Model model) {
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int14")
         .set("table", new String[][]{{"0.01", "3.6518"}, 
         {"0.01447", "3.45283"}, 
         {"0.01895", "3.43918"}, 
         {"0.02342", "3.43962"}, 
         {"0.02789", "3.4406"}, 
         {"0.03236", "3.4413"}, 
         {"0.03683", "3.44161"}, 
         {"0.04131", "3.44175"}, 
         {"0.04578", "3.442"}, 
         {"0.05025", "3.4419"}, 
         {"0.05473", "3.4418"}, 
         {"0.0592", "3.4417"}, 
         {"0.06367", "3.4417"}, 
         {"0.06814", "3.4416"}, 
         {"0.07261", "3.4414"}, 
         {"0.07708", "3.4416"}, 
         {"0.08156", "3.44146"}, 
         {"0.08603", "3.44144"}, 
         {"0.09051", "3.44143"}, 
         {"0.09498", "3.4413"}, 
         {"0.09945", "3.4411"}, 
         {"0.10392", "3.44139"}, 
         {"0.10839", "3.44126"}, 
         {"0.11286", "3.4413"}, 
         {"0.11734", "3.4411"}, 
         {"0.12181", "3.44137"}, 
         {"0.12628", "3.44134"}, 
         {"0.13076", "3.44137"}, 
         {"0.13522", "3.44116"}, 
         {"0.13969", "3.44121"}, 
         {"0.14417", "3.4411"}, 
         {"0.14864", "3.44113"}, 
         {"0.15312", "3.44116"}, 
         {"0.15759", "3.44097"}, 
         {"0.16206", "3.4411"}, 
         {"0.16654", "3.44113"}, 
         {"0.171", "3.44123"}, 
         {"0.17547", "3.4413"}, 
         {"0.17995", "3.4411"}, 
         {"0.18442", "3.44111"}, 
         {"0.18889", "3.44129"}, 
         {"0.19337", "3.4411"}, 
         {"0.19784", "3.4411"}, 
         {"0.20232", "3.4411"}, 
         {"0.20678", "3.4409"}, 
         {"0.21125", "3.44107"}, 
         {"0.21573", "3.4413"}, 
         {"0.2202", "3.44115"}, 
         {"0.22467", "3.4411"}, 
         {"0.22915", "3.44107"}, 
         {"0.23362", "3.4409"}, 
         {"0.23809", "3.44097"}, 
         {"0.24256", "3.4409"}, 
         {"0.24703", "3.44101"}, 
         {"0.25151", "3.4411"}, 
         {"0.25598", "3.44097"}, 
         {"0.26045", "3.4409"}, 
         {"0.26493", "3.44087"}, 
         {"0.2694", "3.4409"}, 
         {"0.27387", "3.4408"}, 
         {"0.27834", "3.44079"}, 
         {"0.28281", "3.44064"}, 
         {"0.28728", "3.44081"}, 
         {"0.29176", "3.44061"}, 
         {"0.29623", "3.44079"}, 
         {"0.30071", "3.4406"}, 
         {"0.30518", "3.4406"}, 
         {"0.30965", "3.44058"}, 
         {"0.31412", "3.4405"}, 
         {"0.31859", "3.44054"}, 
         {"0.32306", "3.4405"}, 
         {"0.32754", "3.44038"}, 
         {"0.33201", "3.44042"}, 
         {"0.33648", "3.4402"}, 
         {"0.34096", "3.4402"}, 
         {"0.34543", "3.4402"}, 
         {"0.34989", "3.44013"}, 
         {"0.35437", "3.43996"}, 
         {"0.35884", "3.44"}, 
         {"0.36332", "3.44"}, 
         {"0.36779", "3.4397"}, 
         {"0.37226", "3.4399"}, 
         {"0.37674", "3.43961"}, 
         {"0.38121", "3.4397"}, 
         {"0.38567", "3.43969"}, 
         {"0.39015", "3.43957"}, 
         {"0.39462", "3.43935"}, 
         {"0.39909", "3.4394"}, 
         {"0.40357", "3.4392"}, 
         {"0.40804", "3.43937"}, 
         {"0.41252", "3.4392"}, 
         {"0.41699", "3.4391"}, 
         {"0.42145", "3.4391"}, 
         {"0.42593", "3.43914"}, 
         {"0.4304", "3.43914"}, 
         {"0.43487", "3.43897"}, 
         {"0.43935", "3.43882"}, 
         {"0.44382", "3.43887"}, 
         {"0.44829", "3.4389"}, 
         {"0.45277", "3.43867"}, 
         {"0.45723", "3.43852"}, 
         {"0.46171", "3.4386"}, 
         {"0.46618", "3.4385"}, 
         {"0.47065", "3.4383"}, 
         {"0.47513", "3.4385"}, 
         {"0.4796", "3.4386"}, 
         {"0.48407", "3.43852"}, 
         {"0.48855", "3.4383"}, 
         {"0.49301", "3.4382"}, 
         {"0.49748", "3.4382"}, 
         {"0.50196", "3.438"}, 
         {"0.50643", "3.43785"}, 
         {"0.51091", "3.4378"}, 
         {"0.51538", "3.43774"}, 
         {"0.51985", "3.43774"}, 
         {"0.52433", "3.4378"}, 
         {"0.52879", "3.4377"}, 
         {"0.53326", "3.4375"}, 
         {"0.53774", "3.43759"}, 
         {"0.54221", "3.43746"}, 
         {"0.54668", "3.43725"}, 
         {"0.55116", "3.43736"}, 
         {"0.55563", "3.43711"}, 
         {"0.56011", "3.4371"}, 
         {"0.56457", "3.4371"}, 
         {"0.56904", "3.43707"}, 
         {"0.57352", "3.4369"}, 
         {"0.57799", "3.4368"}, 
         {"0.58246", "3.4368"}, 
         {"0.58694", "3.4366"}, 
         {"0.59141", "3.43657"}, 
         {"0.59588", "3.43653"}, 
         {"0.60035", "3.43637"}, 
         {"0.60482", "3.4365"}, 
         {"0.60929", "3.4363"}, 
         {"0.61377", "3.4361"}, 
         {"0.61824", "3.436"}, 
         {"0.62272", "3.436"}, 
         {"0.62719", "3.43588"}, 
         {"0.63166", "3.4357"}, 
         {"0.63613", "3.43572"}, 
         {"0.6406", "3.4355"}, 
         {"0.64507", "3.4355"}, 
         {"0.64955", "3.43539"}, 
         {"0.65402", "3.4352"}, 
         {"0.65849", "3.43506"}, 
         {"0.66297", "3.4349"}, 
         {"0.66744", "3.4344"}, 
         {"0.67191", "3.43441"}, 
         {"0.67638", "3.4343"}, 
         {"0.68085", "3.4343"}, 
         {"0.68533", "3.43416"}, 
         {"0.6898", "3.43392"}, 
         {"0.69427", "3.4335"}, 
         {"0.69875", "3.43346"}, 
         {"0.70322", "3.43333"}, 
         {"0.70768", "3.4329"}, 
         {"0.71216", "3.4327"}, 
         {"0.71663", "3.43251"}, 
         {"0.72111", "3.43222"}, 
         {"0.72558", "3.43185"}, 
         {"0.73005", "3.43133"}, 
         {"0.73453", "3.43088"}, 
         {"0.739", "3.4304"}, 
         {"0.74346", "3.42995"}, 
         {"0.74794", "3.42933"}, 
         {"0.75241", "3.4285"}, 
         {"0.75688", "3.4276"}, 
         {"0.76136", "3.4265"}, 
         {"0.76583", "3.42526"}, 
         {"0.77031", "3.42314"}, 
         {"0.77478", "3.42056"}, 
         {"0.77924", "3.41761"}, 
         {"0.78372", "3.41377"}, 
         {"0.78819", "3.41028"}, 
         {"0.79266", "3.40693"}, 
         {"0.79714", "3.4044"}, 
         {"0.80161", "3.40165"}, 
         {"0.80608", "3.39964"}, 
         {"0.81056", "3.39813"}, 
         {"0.81502", "3.39645"}, 
         {"0.81949", "3.39446"}, 
         {"0.82397", "3.39272"}, 
         {"0.82844", "3.39096"}, 
         {"0.83292", "3.38907"}, 
         {"0.83739", "3.38738"}, 
         {"0.84186", "3.38557"}, 
         {"0.84633", "3.3831"}, 
         {"0.8508", "3.37939"}, 
         {"0.85527", "3.37515"}, 
         {"0.85975", "3.3685"}, 
         {"0.86422", "3.3588"}, 
         {"0.86869", "3.34224"}, 
         {"0.87317", "3.31462"}, 
         {"0.87764", "3.2705"}, 
         {"0.88211", "3.19297"}, 
         {"0.88658", "3.05811"}, 
         {"0.89105", "2.86856"}, 
         {"0.89553", "2.54882"}, 
         {"0.9", "2.0359"}});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int14")
         .set("interp", "piecewisecubic");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int14")
         .set("extrap", "linear");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int14")
         .set("fununit", new String[]{"V"});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int14")
         .set("argunit", new String[]{"1"});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int15")
         .label("OCV-LFP\u6700\u7ec8\u7248");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int15")
         .set("funcname", "Eeq_int15");

    return model;
  }

  public static Model run10(Model model) {
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int15")
         .set("table", new String[][]{{"0.011", "3.59852"}, 
         {"0.01196", "3.56477"}, 
         {"0.01293", "3.54036"}, 
         {"0.0139", "3.5227"}, 
         {"0.01488", "3.50841"}, 
         {"0.01585", "3.49592"}, 
         {"0.01683", "3.48578"}, 
         {"0.01781", "3.4769"}, 
         {"0.01879", "3.46915"}, 
         {"0.01978", "3.4627"}, 
         {"0.02076", "3.45707"}, 
         {"0.02174", "3.45242"}, 
         {"0.02272", "3.44849"}, 
         {"0.02369", "3.44515"}, 
         {"0.02467", "3.44264"}, 
         {"0.02565", "3.44042"}, 
         {"0.02663", "3.43855"}, 
         {"0.02761", "3.43709"}, 
         {"0.0286", "3.43583"}, 
         {"0.02958", "3.43486"}, 
         {"0.03056", "3.43404"}, 
         {"0.03154", "3.43337"}, 
         {"0.03252", "3.43283"}, 
         {"0.0335", "3.43233"}, 
         {"0.03447", "3.43196"}, 
         {"0.03546", "3.43165"}, 
         {"0.03644", "3.43141"}, 
         {"0.03742", "3.43116"}, 
         {"0.0384", "3.43096"}, 
         {"0.03938", "3.43085"}, 
         {"0.04036", "3.43071"}, 
         {"0.04134", "3.43062"}, 
         {"0.04232", "3.43049"}, 
         {"0.04331", "3.43039"}, 
         {"0.04429", "3.43034"}, 
         {"0.04526", "3.43029"}, 
         {"0.04624", "3.43024"}, 
         {"0.04722", "3.43017"}, 
         {"0.0482", "3.4301"}, 
         {"0.04918", "3.43008"}, 
         {"0.05017", "3.43007"}, 
         {"0.05115", "3.43008"}, 
         {"0.05213", "3.43006"}, 
         {"0.05311", "3.43006"}, 
         {"0.05409", "3.43006"}, 
         {"0.05507", "3.43005"}, 
         {"0.05605", "3.43004"}, 
         {"0.05704", "3.43004"}, 
         {"0.05801", "3.43001"}, 
         {"0.05899", "3.42999"}, 
         {"0.05997", "3.42996"}, 
         {"0.06095", "3.4299"}, 
         {"0.06193", "3.42982"}, 
         {"0.06291", "3.4298"}, 
         {"0.06389", "3.42984"}, 
         {"0.06488", "3.42981"}, 
         {"0.06586", "3.4298"}, 
         {"0.06684", "3.42976"}, 
         {"0.06782", "3.42978"}, 
         {"0.06879", "3.42974"}, 
         {"0.06977", "3.42977"}, 
         {"0.07075", "3.42975"}, 
         {"0.07174", "3.42973"}, 
         {"0.07272", "3.42973"}, 
         {"0.0737", "3.42973"}, 
         {"0.07468", "3.42975"}, 
         {"0.07566", "3.42974"}, 
         {"0.07664", "3.42973"}, 
         {"0.07762", "3.42972"}, 
         {"0.07861", "3.42969"}, 
         {"0.07959", "3.42964"}, 
         {"0.08056", "3.42966"}, 
         {"0.08154", "3.42966"}, 
         {"0.08252", "3.42966"}, 
         {"0.0835", "3.42966"}, 
         {"0.08448", "3.42963"}, 
         {"0.08546", "3.4296"}, 
         {"0.08645", "3.42957"}, 
         {"0.08743", "3.42958"}, 
         {"0.08841", "3.42957"}, 
         {"0.08939", "3.42956"}, 
         {"0.09037", "3.42963"}, 
         {"0.09134", "3.42953"}, 
         {"0.09232", "3.42954"}, 
         {"0.09331", "3.42954"}, 
         {"0.09429", "3.42948"}, 
         {"0.09527", "3.42947"}, 
         {"0.09625", "3.42947"}, 
         {"0.09723", "3.42944"}, 
         {"0.09821", "3.42946"}, 
         {"0.09919", "3.42946"}, 
         {"0.10018", "3.42944"}, 
         {"0.10116", "3.42944"}, 
         {"0.10214", "3.42945"}, 
         {"0.10311", "3.42942"}, 
         {"0.10409", "3.4294"}, 
         {"0.10507", "3.42942"}, 
         {"0.10605", "3.42941"}, 
         {"0.10704", "3.42937"}, 
         {"0.10802", "3.42938"}, 
         {"0.109", "3.42939"}, 
         {"0.10998", "3.42941"}, 
         {"0.11096", "3.42941"}, 
         {"0.11194", "3.42936"}, 
         {"0.11292", "3.42939"}, 
         {"0.11389", "3.42937"}, 
         {"0.11488", "3.42938"}, 
         {"0.11586", "3.42934"}, 
         {"0.11684", "3.42935"}, 
         {"0.11782", "3.42936"}, 
         {"0.1188", "3.42936"}, 
         {"0.11978", "3.42937"}, 
         {"0.12076", "3.42931"}, 
         {"0.12175", "3.42928"}, 
         {"0.12273", "3.42927"}, 
         {"0.12371", "3.42927"}, 
         {"0.12469", "3.42922"}, 
         {"0.12566", "3.42922"}, 
         {"0.12664", "3.4292"}, 
         {"0.12762", "3.42918"}, 
         {"0.12861", "3.42919"}, 
         {"0.12959", "3.42916"}, 
         {"0.13057", "3.42917"}, 
         {"0.13155", "3.42918"}, 
         {"0.13253", "3.42918"}, 
         {"0.13351", "3.42917"}, 
         {"0.13449", "3.42913"}, 
         {"0.13547", "3.42914"}, 
         {"0.13645", "3.42908"}, 
         {"0.13743", "3.4291"}, 
         {"0.13841", "3.42908"}, 
         {"0.13939", "3.42905"}, 
         {"0.14037", "3.42908"}, 
         {"0.14135", "3.42905"}, 
         {"0.14233", "3.42902"}, 
         {"0.14332", "3.42903"}, 
         {"0.1443", "3.42897"}, 
         {"0.14528", "3.42895"}, 
         {"0.14626", "3.42889"}, 
         {"0.14724", "3.42887"}, 
         {"0.14821", "3.42885"}, 
         {"0.14919", "3.42881"}, 
         {"0.15018", "3.42885"}, 
         {"0.15116", "3.42882"}, 
         {"0.15214", "3.42882"}, 
         {"0.15312", "3.42888"}, 
         {"0.1541", "3.42885"}, 
         {"0.15508", "3.42878"}, 
         {"0.15606", "3.42875"}, 
         {"0.15704", "3.4288"}, 
         {"0.15803", "3.42874"}, 
         {"0.15901", "3.4287"}, 
         {"0.15998", "3.42869"}, 
         {"0.16096", "3.42869"}, 
         {"0.16194", "3.42868"}, 
         {"0.16292", "3.42869"}, 
         {"0.1639", "3.42868"}, 
         {"0.16489", "3.42865"}, 
         {"0.16587", "3.42864"}, 
         {"0.16685", "3.42866"}, 
         {"0.16783", "3.42864"}, 
         {"0.16881", "3.42863"}, 
         {"0.16978", "3.42861"}, 
         {"0.17076", "3.42864"}, 
         {"0.17175", "3.42861"}, 
         {"0.17273", "3.42861"}, 
         {"0.17371", "3.4286"}, 
         {"0.17469", "3.42862"}, 
         {"0.17567", "3.42864"}, 
         {"0.17665", "3.42861"}, 
         {"0.17763", "3.42856"}, 
         {"0.17861", "3.42859"}, 
         {"0.1796", "3.42859"}, 
         {"0.18058", "3.42856"}, 
         {"0.18156", "3.42855"}, 
         {"0.18253", "3.42854"}, 
         {"0.18351", "3.42854"}, 
         {"0.18449", "3.42855"}, 
         {"0.18547", "3.42854"}, 
         {"0.18646", "3.42847"}, 
         {"0.18744", "3.42849"}, 
         {"0.18842", "3.42845"}, 
         {"0.1894", "3.42846"}, 
         {"0.19038", "3.42845"}, 
         {"0.19136", "3.42843"}, 
         {"0.19234", "3.42845"}, 
         {"0.19333", "3.42844"}, 
         {"0.1943", "3.42841"}, 
         {"0.19528", "3.4284"}, 
         {"0.19626", "3.42837"}, 
         {"0.19724", "3.42838"}, 
         {"0.19822", "3.42837"}, 
         {"0.1992", "3.42838"}, 
         {"0.20018", "3.4284"}, 
         {"0.20117", "3.42839"}, 
         {"0.20215", "3.42838"}, 
         {"0.20313", "3.42837"}, 
         {"0.20411", "3.42836"}, 
         {"0.20508", "3.42832"}, 
         {"0.20606", "3.42828"}, 
         {"0.20704", "3.42829"}, 
         {"0.20803", "3.42829"}, 
         {"0.20901", "3.42833"}, 
         {"0.20999", "3.42828"}, 
         {"0.21097", "3.42826"}, 
         {"0.21195", "3.42826"}, 
         {"0.21293", "3.42829"}, 
         {"0.21391", "3.42825"}, 
         {"0.2149", "3.42828"}, 
         {"0.21588", "3.42826"}, 
         {"0.21685", "3.42826"}, 
         {"0.21783", "3.42817"}, 
         {"0.21881", "3.4282"}, 
         {"0.21979", "3.42827"}, 
         {"0.22077", "3.42821"}, 
         {"0.22176", "3.42819"}, 
         {"0.22274", "3.42813"}, 
         {"0.22372", "3.42815"}, 
         {"0.2247", "3.42817"}, 
         {"0.22568", "3.42816"}, 
         {"0.22666", "3.42814"}, 
         {"0.22763", "3.42816"}, 
         {"0.22861", "3.42813"}, 
         {"0.2296", "3.4281"}, 
         {"0.23058", "3.42811"}, 
         {"0.23156", "3.42809"}, 
         {"0.23254", "3.4281"}, 
         {"0.23352", "3.42809"}, 
         {"0.2345", "3.42806"}, 
         {"0.23548", "3.42806"}, 
         {"0.23647", "3.42807"}, 
         {"0.23745", "3.42806"}, 
         {"0.23843", "3.42806"}, 
         {"0.2394", "3.42805"}, 
         {"0.24038", "3.42807"}, 
         {"0.24136", "3.42806"}, 
         {"0.24234", "3.42805"}, 
         {"0.24333", "3.42808"}, 
         {"0.24431", "3.42803"}, 
         {"0.24529", "3.42803"}, 
         {"0.24627", "3.42805"}, 
         {"0.24725", "3.42801"}, 
         {"0.24823", "3.42799"}, 
         {"0.24921", "3.428"}, 
         {"0.25018", "3.42797"}, 
         {"0.25117", "3.42796"}, 
         {"0.25215", "3.42796"}, 
         {"0.25313", "3.42796"}, 
         {"0.25411", "3.42797"}, 
         {"0.25509", "3.42794"}, 
         {"0.25607", "3.4279"}, 
         {"0.25705", "3.4279"}, 
         {"0.25804", "3.4279"}, 
         {"0.25902", "3.42791"}, 
         {"0.26", "3.42794"}, 
         {"0.26098", "3.42793"}, 
         {"0.26195", "3.42791"}, 
         {"0.26293", "3.42788"}, 
         {"0.26391", "3.42787"}, 
         {"0.2649", "3.42782"}, 
         {"0.26588", "3.42794"}, 
         {"0.26686", "3.42794"}, 
         {"0.26784", "3.42787"}, 
         {"0.26882", "3.42787"}, 
         {"0.2698", "3.42782"}, 
         {"0.27078", "3.42787"}, 
         {"0.27176", "3.42782"}, 
         {"0.27275", "3.42782"}, 
         {"0.27372", "3.4278"}, 
         {"0.2747", "3.42786"}, 
         {"0.27568", "3.4278"}, 
         {"0.27666", "3.42782"}, 
         {"0.27764", "3.4278"}, 
         {"0.27862", "3.42781"}, 
         {"0.27961", "3.4278"}, 
         {"0.28059", "3.42779"}, 
         {"0.28157", "3.42778"}, 
         {"0.28255", "3.42779"}, 
         {"0.28352", "3.42779"}, 
         {"0.2845", "3.42776"}, 
         {"0.28548", "3.42778"}, 
         {"0.28647", "3.42776"}, 
         {"0.28745", "3.42776"}, 
         {"0.28843", "3.42775"}, 
         {"0.28941", "3.42775"}, 
         {"0.29039", "3.42771"}, 
         {"0.29137", "3.42773"}, 
         {"0.29235", "3.42775"}, 
         {"0.29333", "3.42773"}, 
         {"0.29432", "3.42772"}, 
         {"0.2953", "3.42768"}, 
         {"0.29627", "3.42771"}, 
         {"0.29725", "3.4277"}, 
         {"0.29823", "3.42768"}, 
         {"0.29921", "3.4277"}, 
         {"0.30019", "3.42768"}, 
         {"0.30118", "3.4277"}, 
         {"0.30216", "3.42768"}, 
         {"0.30314", "3.42768"}, 
         {"0.30412", "3.42769"}, 
         {"0.3051", "3.42767"}, 
         {"0.30608", "3.42766"}, 
         {"0.30705", "3.42763"}, 
         {"0.30804", "3.42761"}, 
         {"0.30902", "3.42761"}, 
         {"0.31", "3.42764"}, 
         {"0.31098", "3.42761"}, 
         {"0.31196", "3.42763"}, 
         {"0.31294", "3.42765"}, 
         {"0.31392", "3.42758"}, 
         {"0.31491", "3.42766"}, 
         {"0.31589", "3.42764"}, 
         {"0.31687", "3.42766"}, 
         {"0.31784", "3.42766"}, 
         {"0.31882", "3.42769"}, 
         {"0.3198", "3.42767"}, 
         {"0.32078", "3.42758"}, 
         {"0.32176", "3.42758"}, 
         {"0.32275", "3.42757"}, 
         {"0.32373", "3.42761"}, 
         {"0.32471", "3.42756"}, 
         {"0.32569", "3.42752"}, 
         {"0.32667", "3.4275"}, 
         {"0.32765", "3.42748"}, 
         {"0.32863", "3.42748"}, 
         {"0.32962", "3.42749"}, 
         {"0.33059", "3.42751"}, 
         {"0.33157", "3.42748"}, 
         {"0.33255", "3.42746"}, 
         {"0.33353", "3.42746"}, 
         {"0.33451", "3.42747"}, 
         {"0.33549", "3.42746"}, 
         {"0.33648", "3.42747"}, 
         {"0.33746", "3.42747"}, 
         {"0.33844", "3.42744"}, 
         {"0.33942", "3.42737"}, 
         {"0.3404", "3.42739"}, 
         {"0.34137", "3.42742"}, 
         {"0.34235", "3.42743"}, 
         {"0.34333", "3.42743"}, 
         {"0.34432", "3.42738"}, 
         {"0.3453", "3.42738"}, 
         {"0.34628", "3.4274"}, 
         {"0.34726", "3.42738"}, 
         {"0.34824", "3.42741"}, 
         {"0.34922", "3.42738"}, 
         {"0.3502", "3.42739"}, 
         {"0.35119", "3.42735"}, 
         {"0.35217", "3.42731"}, 
         {"0.35314", "3.42738"}, 
         {"0.35412", "3.42736"}, 
         {"0.3551", "3.42735"}, 
         {"0.35608", "3.42732"}, 
         {"0.35706", "3.42737"}, 
         {"0.35805", "3.42733"}, 
         {"0.35903", "3.42732"}, 
         {"0.36001", "3.4273"}, 
         {"0.36099", "3.4273"}, 
         {"0.36197", "3.4273"}, 
         {"0.36295", "3.42729"}, 
         {"0.36392", "3.42728"}, 
         {"0.3649", "3.42728"}, 
         {"0.36589", "3.42728"}, 
         {"0.36687", "3.42728"}, 
         {"0.36785", "3.42727"}, 
         {"0.36883", "3.4273"}, 
         {"0.36981", "3.42726"}, 
         {"0.37079", "3.42726"}, 
         {"0.37177", "3.42727"}, 
         {"0.37275", "3.42726"}, 
         {"0.37373", "3.42728"}, 
         {"0.3747", "3.42727"}, 
         {"0.37568", "3.42729"}, 
         {"0.37666", "3.42726"}, 
         {"0.37764", "3.42729"}, 
         {"0.37862", "3.42726"}, 
         {"0.37961", "3.42729"}, 
         {"0.38059", "3.42727"}, 
         {"0.38157", "3.42728"}, 
         {"0.38255", "3.42728"}, 
         {"0.38353", "3.42728"}, 
         {"0.38451", "3.42729"}, 
         {"0.38548", "3.42728"}, 
         {"0.38646", "3.42727"}, 
         {"0.38745", "3.42727"}, 
         {"0.38843", "3.42726"}, 
         {"0.38941", "3.42725"}, 
         {"0.39039", "3.42726"}, 
         {"0.39137", "3.42727"}, 
         {"0.39235", "3.42726"}, 
         {"0.39333", "3.42727"}, 
         {"0.39432", "3.42725"}, 
         {"0.3953", "3.42726"}, 
         {"0.39628", "3.42727"}, 
         {"0.39725", "3.42725"}, 
         {"0.39823", "3.42726"}, 
         {"0.39921", "3.42723"}, 
         {"0.40019", "3.42723"}, 
         {"0.40118", "3.4272"}, 
         {"0.40216", "3.42719"}, 
         {"0.40314", "3.42717"}, 
         {"0.40412", "3.42717"}, 
         {"0.4051", "3.42715"}, 
         {"0.40608", "3.42711"}, 
         {"0.40706", "3.42716"}, 
         {"0.40805", "3.42712"}, 
         {"0.40902", "3.42717"}, 
         {"0.41", "3.42706"}, 
         {"0.41098", "3.42711"}, 
         {"0.41196", "3.42715"}, 
         {"0.41294", "3.42709"}, 
         {"0.41392", "3.42714"}, 
         {"0.4149", "3.42711"}, 
         {"0.41589", "3.42715"}, 
         {"0.41687", "3.42715"}, 
         {"0.41785", "3.42718"}, 
         {"0.41883", "3.42716"}, 
         {"0.4198", "3.42714"}, 
         {"0.42078", "3.42717"}, 
         {"0.42176", "3.42712"}, 
         {"0.42275", "3.42706"}, 
         {"0.42373", "3.42707"}, 
         {"0.42471", "3.42705"}, 
         {"0.42569", "3.42707"}, 
         {"0.42667", "3.42708"}, 
         {"0.42765", "3.42708"}, 
         {"0.42863", "3.4271"}, 
         {"0.42962", "3.42704"}, 
         {"0.4306", "3.42703"}, 
         {"0.43157", "3.42708"}, 
         {"0.43255", "3.42703"}, 
         {"0.43353", "3.427"}, 
         {"0.43451", "3.42699"}, 
         {"0.43549", "3.42697"}, 
         {"0.43647", "3.427"}, 
         {"0.43746", "3.42698"}, 
         {"0.43844", "3.42699"}, 
         {"0.43942", "3.42696"}, 
         {"0.4404", "3.42695"}, 
         {"0.44138", "3.42697"}, 
         {"0.44235", "3.42696"}, 
         {"0.44333", "3.42694"}, 
         {"0.44432", "3.42693"}, 
         {"0.4453", "3.42696"}, 
         {"0.44628", "3.42695"}, 
         {"0.44726", "3.42693"}, 
         {"0.44824", "3.42693"}, 
         {"0.44922", "3.42692"}, 
         {"0.4502", "3.4269"}, 
         {"0.45119", "3.42689"}, 
         {"0.45217", "3.42685"}, 
         {"0.45315", "3.42686"}, 
         {"0.45412", "3.42688"}, 
         {"0.4551", "3.42688"}, 
         {"0.45608", "3.42685"}, 
         {"0.45706", "3.42681"}, 
         {"0.45804", "3.42683"}, 
         {"0.45903", "3.42684"}, 
         {"0.46001", "3.42687"}, 
         {"0.46099", "3.42684"}, 
         {"0.46197", "3.42677"}, 
         {"0.46295", "3.42682"}, 
         {"0.46393", "3.42678"}, 
         {"0.4649", "3.42678"}, 
         {"0.46589", "3.42675"}, 
         {"0.46687", "3.42678"}, 
         {"0.46785", "3.42679"}, 
         {"0.46883", "3.42675"}, 
         {"0.46981", "3.42678"}, 
         {"0.47079", "3.42674"}, 
         {"0.47177", "3.42674"}, 
         {"0.47276", "3.42675"}, 
         {"0.47374", "3.42676"}, 
         {"0.47472", "3.42671"}, 
         {"0.4757", "3.42672"}, 
         {"0.47667", "3.4267"}, 
         {"0.47765", "3.42671"}, 
         {"0.47863", "3.42669"}, 
         {"0.47961", "3.4267"}, 
         {"0.4806", "3.42671"}, 
         {"0.48158", "3.42669"}, 
         {"0.48256", "3.42667"}, 
         {"0.48354", "3.42664"}, 
         {"0.48452", "3.42664"}, 
         {"0.4855", "3.42661"}, 
         {"0.48648", "3.42659"}, 
         {"0.48747", "3.42659"}, 
         {"0.48844", "3.42655"}, 
         {"0.48942", "3.42658"}, 
         {"0.4904", "3.42654"}, 
         {"0.49138", "3.42658"}, 
         {"0.49236", "3.42657"}, 
         {"0.49334", "3.42661"}, 
         {"0.49433", "3.42661"}, 
         {"0.49531", "3.42661"}, 
         {"0.49629", "3.42664"}, 
         {"0.49727", "3.42664"}, 
         {"0.49825", "3.42665"}, 
         {"0.49922", "3.42664"}, 
         {"0.5002", "3.42662"}, 
         {"0.50118", "3.42661"}, 
         {"0.50217", "3.42661"}, 
         {"0.50315", "3.42659"}, 
         {"0.50413", "3.42659"}, 
         {"0.50511", "3.4266"}, 
         {"0.50609", "3.42661"}, 
         {"0.50707", "3.42662"}, 
         {"0.50805", "3.42662"}, 
         {"0.50904", "3.42662"}, 
         {"0.51002", "3.42662"}, 
         {"0.51099", "3.42663"}, 
         {"0.51197", "3.42664"}, 
         {"0.51295", "3.42665"}, 
         {"0.51393", "3.42664"}, 
         {"0.51491", "3.42666"}, 
         {"0.5159", "3.42663"}, 
         {"0.51688", "3.42665"}, 
         {"0.51786", "3.4266"}, 
         {"0.51884", "3.42658"}, 
         {"0.51982", "3.42659"}, 
         {"0.5208", "3.42655"}, 
         {"0.52177", "3.42655"}, 
         {"0.52276", "3.4265"}, 
         {"0.52374", "3.42652"}, 
         {"0.52472", "3.4265"}, 
         {"0.5257", "3.42648"}, 
         {"0.52668", "3.4265"}, 
         {"0.52766", "3.42649"}, 
         {"0.52864", "3.42648"}, 
         {"0.52962", "3.42646"}, 
         {"0.53061", "3.42641"}, 
         {"0.53159", "3.42638"}, 
         {"0.53257", "3.42636"}, 
         {"0.53354", "3.42637"}, 
         {"0.53452", "3.42636"}, 
         {"0.5355", "3.42636"}, 
         {"0.53648", "3.42636"}, 
         {"0.53747", "3.42633"}, 
         {"0.53845", "3.42629"}, 
         {"0.53943", "3.42627"}, 
         {"0.54041", "3.42623"}, 
         {"0.54139", "3.42624"}, 
         {"0.54237", "3.42624"}, 
         {"0.54335", "3.42624"}, 
         {"0.54434", "3.42624"}, 
         {"0.54531", "3.42621"}, 
         {"0.54629", "3.4262"}, 
         {"0.54727", "3.42624"}, 
         {"0.54825", "3.42619"}, 
         {"0.54923", "3.42612"}, 
         {"0.55021", "3.4261"}, 
         {"0.55119", "3.42608"}, 
         {"0.55218", "3.42608"}, 
         {"0.55316", "3.42606"}, 
         {"0.55414", "3.42607"}, 
         {"0.55512", "3.42605"}, 
         {"0.55609", "3.42604"}, 
         {"0.55707", "3.42602"}, 
         {"0.55805", "3.42603"}, 
         {"0.55904", "3.42601"}, 
         {"0.56002", "3.426"}, 
         {"0.561", "3.42601"}, 
         {"0.56198", "3.42596"}, 
         {"0.56296", "3.4259"}, 
         {"0.56394", "3.42595"}, 
         {"0.56492", "3.42591"}, 
         {"0.56591", "3.42594"}, 
         {"0.56688", "3.42591"}, 
         {"0.56786", "3.42586"}, 
         {"0.56884", "3.42587"}, 
         {"0.56982", "3.42578"}, 
         {"0.5708", "3.42579"}, 
         {"0.57178", "3.42581"}, 
         {"0.57276", "3.42585"}, 
         {"0.57375", "3.42576"}, 
         {"0.57473", "3.42576"}, 
         {"0.57571", "3.4258"}, 
         {"0.57669", "3.42573"}, 
         {"0.57767", "3.42574"}, 
         {"0.57864", "3.42577"}, 
         {"0.57962", "3.42569"}, 
         {"0.58061", "3.42564"}, 
         {"0.58159", "3.42567"}, 
         {"0.58257", "3.42563"}, 
         {"0.58355", "3.4256"}, 
         {"0.58453", "3.4256"}, 
         {"0.58551", "3.42562"}, 
         {"0.58649", "3.4256"}, 
         {"0.58748", "3.42559"}, 
         {"0.58846", "3.42559"}, 
         {"0.58944", "3.42558"}, 
         {"0.59041", "3.4256"}, 
         {"0.59139", "3.4256"}, 
         {"0.59237", "3.42561"}, 
         {"0.59335", "3.4256"}, 
         {"0.59433", "3.42559"}, 
         {"0.59532", "3.4256"}, 
         {"0.5963", "3.42558"}, 
         {"0.59728", "3.42557"}, 
         {"0.59826", "3.42556"}, 
         {"0.59924", "3.42553"}, 
         {"0.60022", "3.42558"}, 
         {"0.60119", "3.42551"}, 
         {"0.60218", "3.42553"}, 
         {"0.60316", "3.42553"}, 
         {"0.60414", "3.42552"}, 
         {"0.60512", "3.4255"}, 
         {"0.6061", "3.42549"}, 
         {"0.60708", "3.42545"}, 
         {"0.60806", "3.42541"}, 
         {"0.60905", "3.42544"}, 
         {"0.61003", "3.42543"}, 
         {"0.61101", "3.42544"}, 
         {"0.61199", "3.42545"}, 
         {"0.61296", "3.42542"}, 
         {"0.61394", "3.42539"}, 
         {"0.61492", "3.42539"}, 
         {"0.61591", "3.42536"}, 
         {"0.61689", "3.42538"}, 
         {"0.61787", "3.42539"}, 
         {"0.61885", "3.42542"}, 
         {"0.61983", "3.42541"}, 
         {"0.62081", "3.42536"}, 
         {"0.62179", "3.42534"}, 
         {"0.62277", "3.42534"}, 
         {"0.62376", "3.42533"}, 
         {"0.62473", "3.42529"}, 
         {"0.62571", "3.42531"}, 
         {"0.62669", "3.42529"}, 
         {"0.62767", "3.42528"}, 
         {"0.62865", "3.42528"}, 
         {"0.62963", "3.42528"}, 
         {"0.63062", "3.42527"}, 
         {"0.6316", "3.42529"}, 
         {"0.63258", "3.42527"}, 
         {"0.63356", "3.4253"}, 
         {"0.63453", "3.42529"}, 
         {"0.63551", "3.42525"}, 
         {"0.63649", "3.42528"}, 
         {"0.63748", "3.42523"}, 
         {"0.63846", "3.42526"}, 
         {"0.63944", "3.42522"}, 
         {"0.64042", "3.42522"}, 
         {"0.6414", "3.42515"}, 
         {"0.64238", "3.42515"}, 
         {"0.64336", "3.42517"}, 
         {"0.64434", "3.42514"}, 
         {"0.64533", "3.42516"}, 
         {"0.64631", "3.42511"}, 
         {"0.64728", "3.42501"}, 
         {"0.64826", "3.42498"}, 
         {"0.64924", "3.42496"}, 
         {"0.65022", "3.42495"}, 
         {"0.6512", "3.42495"}, 
         {"0.65219", "3.42494"}, 
         {"0.65317", "3.42494"}, 
         {"0.65415", "3.42486"}, 
         {"0.65513", "3.42488"}, 
         {"0.65611", "3.42484"}, 
         {"0.65709", "3.42486"}, 
         {"0.65806", "3.42482"}, 
         {"0.65905", "3.42484"}, 
         {"0.66003", "3.42474"}, 
         {"0.66101", "3.42469"}, 
         {"0.66199", "3.42467"}, 
         {"0.66297", "3.42467"}, 
         {"0.66395", "3.42466"}, 
         {"0.66493", "3.42464"}, 
         {"0.66591", "3.42458"}, 
         {"0.6669", "3.42461"}, 
         {"0.66788", "3.4246"}, 
         {"0.66885", "3.42457"}, 
         {"0.66983", "3.4245"}, 
         {"0.67081", "3.42457"}, 
         {"0.67179", "3.42457"}, 
         {"0.67277", "3.42456"}, 
         {"0.67376", "3.42452"}, 
         {"0.67474", "3.42448"}, 
         {"0.67572", "3.42447"}, 
         {"0.6767", "3.42435"}, 
         {"0.67768", "3.42433"}, 
         {"0.67866", "3.42429"}, 
         {"0.67963", "3.42424"}, 
         {"0.68063", "3.42423"}, 
         {"0.6816", "3.4242"}, 
         {"0.68258", "3.42421"}, 
         {"0.68356", "3.42422"}, 
         {"0.68454", "3.42419"}, 
         {"0.68552", "3.42419"}, 
         {"0.6865", "3.4242"}, 
         {"0.68748", "3.42421"}, 
         {"0.68847", "3.42421"}, 
         {"0.68945", "3.42418"}, 
         {"0.69043", "3.42416"}, 
         {"0.69141", "3.42417"}, 
         {"0.69238", "3.42416"}, 
         {"0.69336", "3.42414"}, 
         {"0.69434", "3.42413"}, 
         {"0.69533", "3.42412"}, 
         {"0.69631", "3.4241"}, 
         {"0.69729", "3.42407"}, 
         {"0.69827", "3.42405"}, 
         {"0.69925", "3.42402"}, 
         {"0.70023", "3.42395"}, 
         {"0.70121", "3.42402"}, 
         {"0.7022", "3.42392"}, 
         {"0.70317", "3.42393"}, 
         {"0.70415", "3.42389"}, 
         {"0.70513", "3.42386"}, 
         {"0.70611", "3.42387"}, 
         {"0.70709", "3.42388"}, 
         {"0.70807", "3.42386"}, 
         {"0.70906", "3.42385"}, 
         {"0.71004", "3.42385"}, 
         {"0.71102", "3.42383"}, 
         {"0.712", "3.4238"}, 
         {"0.71298", "3.42373"}, 
         {"0.71396", "3.42368"}, 
         {"0.71493", "3.42372"}, 
         {"0.71591", "3.42373"}, 
         {"0.7169", "3.42367"}, 
         {"0.71788", "3.42359"}, 
         {"0.71886", "3.42359"}, 
         {"0.71984", "3.42361"}, 
         {"0.72082", "3.42357"}, 
         {"0.7218", "3.42354"}, 
         {"0.72278", "3.42354"}, 
         {"0.72377", "3.42357"}, 
         {"0.72475", "3.42357"}, 
         {"0.72572", "3.42356"}, 
         {"0.7267", "3.42353"}, 
         {"0.72768", "3.42349"}, 
         {"0.72866", "3.42348"}, 
         {"0.72964", "3.42337"}, 
         {"0.73063", "3.42336"}, 
         {"0.73161", "3.42337"}, 
         {"0.73259", "3.42335"}, 
         {"0.73357", "3.4233"}, 
         {"0.73455", "3.4233"}, 
         {"0.73553", "3.42334"}, 
         {"0.7365", "3.42326"}, 
         {"0.73748", "3.42324"}, 
         {"0.73847", "3.42321"}, 
         {"0.73945", "3.42315"}, 
         {"0.74043", "3.42318"}, 
         {"0.74141", "3.42317"}, 
         {"0.74239", "3.42317"}, 
         {"0.74337", "3.42318"}, 
         {"0.74435", "3.42314"}, 
         {"0.74534", "3.42312"}, 
         {"0.74632", "3.42302"}, 
         {"0.7473", "3.423"}, 
         {"0.74828", "3.42298"}, 
         {"0.74925", "3.42297"}, 
         {"0.75023", "3.42296"}, 
         {"0.75121", "3.42294"}, 
         {"0.7522", "3.42293"}, 
         {"0.75318", "3.42286"}, 
         {"0.75416", "3.42285"}, 
         {"0.75514", "3.4228"}, 
         {"0.75612", "3.42279"}, 
         {"0.7571", "3.42274"}, 
         {"0.75808", "3.42263"}, 
         {"0.75906", "3.42262"}, 
         {"0.76005", "3.42261"}, 
         {"0.76102", "3.42254"}, 
         {"0.762", "3.42254"}, 
         {"0.76298", "3.42249"}, 
         {"0.76396", "3.42249"}, 
         {"0.76494", "3.42249"}, 
         {"0.76592", "3.42247"}, 
         {"0.76691", "3.42247"}, 
         {"0.76789", "3.42243"}, 
         {"0.76887", "3.4224"}, 
         {"0.76985", "3.42233"}, 
         {"0.77083", "3.42232"}, 
         {"0.7718", "3.42235"}, 
         {"0.77278", "3.42226"}, 
         {"0.77377", "3.42224"}, 
         {"0.77475", "3.42225"}, 
         {"0.77573", "3.42221"}, 
         {"0.77671", "3.42219"}, 
         {"0.77769", "3.42217"}, 
         {"0.77867", "3.42215"}, 
         {"0.77965", "3.42216"}, 
         {"0.78063", "3.42213"}, 
         {"0.78162", "3.42215"}, 
         {"0.7826", "3.4221"}, 
         {"0.78357", "3.42205"}, 
         {"0.78455", "3.42209"}, 
         {"0.78553", "3.42204"}, 
         {"0.78651", "3.42204"}, 
         {"0.78749", "3.42195"}, 
         {"0.78848", "3.42191"}, 
         {"0.78946", "3.42189"}, 
         {"0.79044", "3.42186"}, 
         {"0.79142", "3.42181"}, 
         {"0.7924", "3.42182"}, 
         {"0.79338", "3.42181"}, 
         {"0.79435", "3.42178"}, 
         {"0.79534", "3.42177"}, 
         {"0.79632", "3.42174"}, 
         {"0.7973", "3.42175"}, 
         {"0.79828", "3.42164"}, 
         {"0.79926", "3.42157"}, 
         {"0.80024", "3.42154"}, 
         {"0.80122", "3.42149"}, 
         {"0.80221", "3.42145"}, 
         {"0.80319", "3.42134"}, 
         {"0.80417", "3.4213"}, 
         {"0.80515", "3.42126"}, 
         {"0.80612", "3.42123"}, 
         {"0.8071", "3.42116"}, 
         {"0.80808", "3.42111"}, 
         {"0.80906", "3.42107"}, 
         {"0.81005", "3.42106"}, 
         {"0.81103", "3.42103"}, 
         {"0.81201", "3.42099"}, 
         {"0.81299", "3.42097"}, 
         {"0.81397", "3.42096"}, 
         {"0.81495", "3.42089"}, 
         {"0.81593", "3.42086"}, 
         {"0.81692", "3.42079"}, 
         {"0.81789", "3.42078"}, 
         {"0.81887", "3.42077"}, 
         {"0.81985", "3.42073"}, 
         {"0.82083", "3.42068"}, 
         {"0.82181", "3.42056"}, 
         {"0.82279", "3.42052"}, 
         {"0.82378", "3.42049"}, 
         {"0.82476", "3.42049"}, 
         {"0.82574", "3.42046"}, 
         {"0.82672", "3.42041"}, 
         {"0.8277", "3.4204"}, 
         {"0.82867", "3.42033"}, 
         {"0.82965", "3.42026"}, 
         {"0.83063", "3.42021"}, 
         {"0.83162", "3.42017"}, 
         {"0.8326", "3.42014"}, 
         {"0.83358", "3.4201"}, 
         {"0.83456", "3.42009"}, 
         {"0.83554", "3.42001"}, 
         {"0.83652", "3.41991"}, 
         {"0.8375", "3.41989"}, 
         {"0.83849", "3.4199"}, 
         {"0.83947", "3.41988"}, 
         {"0.84044", "3.41985"}, 
         {"0.84142", "3.4198"}, 
         {"0.8424", "3.41971"}, 
         {"0.84338", "3.41969"}, 
         {"0.84436", "3.41958"}, 
         {"0.84535", "3.41949"}, 
         {"0.84633", "3.41944"}, 
         {"0.84731", "3.41941"}, 
         {"0.84829", "3.41939"}, 
         {"0.84927", "3.41937"}, 
         {"0.85025", "3.41933"}, 
         {"0.85122", "3.41928"}, 
         {"0.8522", "3.41922"}, 
         {"0.85319", "3.41915"}, 
         {"0.85417", "3.41906"}, 
         {"0.85515", "3.41903"}, 
         {"0.85613", "3.41897"}, 
         {"0.85711", "3.41889"}, 
         {"0.85809", "3.41881"}, 
         {"0.85907", "3.41878"}, 
         {"0.86006", "3.41875"}, 
         {"0.86104", "3.41867"}, 
         {"0.86202", "3.41854"}, 
         {"0.86299", "3.41851"}, 
         {"0.86397", "3.41847"}, 
         {"0.86495", "3.41841"}, 
         {"0.86593", "3.41834"}, 
         {"0.86692", "3.4182"}, 
         {"0.8679", "3.41811"}, 
         {"0.86888", "3.41802"}, 
         {"0.86986", "3.41798"}, 
         {"0.87084", "3.41789"}, 
         {"0.87182", "3.41779"}, 
         {"0.8728", "3.41772"}, 
         {"0.87377", "3.41765"}, 
         {"0.87476", "3.41755"}, 
         {"0.87574", "3.41747"}, 
         {"0.87672", "3.41739"}, 
         {"0.8777", "3.41731"}, 
         {"0.87868", "3.41725"}, 
         {"0.87966", "3.41711"}, 
         {"0.88064", "3.41701"}, 
         {"0.88163", "3.41685"}, 
         {"0.88261", "3.41678"}, 
         {"0.88359", "3.4167"}, 
         {"0.88457", "3.41651"}, 
         {"0.88554", "3.41635"}, 
         {"0.88652", "3.41624"}, 
         {"0.8875", "3.41612"}, 
         {"0.88849", "3.41597"}, 
         {"0.88947", "3.41586"}, 
         {"0.89045", "3.41571"}, 
         {"0.89143", "3.41563"}, 
         {"0.89241", "3.41549"}, 
         {"0.89339", "3.41532"}, 
         {"0.89437", "3.41516"}, 
         {"0.89535", "3.415"}, 
         {"0.89634", "3.41489"}, 
         {"0.89731", "3.41478"}, 
         {"0.89829", "3.41463"}, 
         {"0.89927", "3.41454"}, 
         {"0.90025", "3.41434"}, 
         {"0.90123", "3.4142"}, 
         {"0.90221", "3.41398"}, 
         {"0.9032", "3.41385"}, 
         {"0.90418", "3.41364"}, 
         {"0.90516", "3.41346"}, 
         {"0.90614", "3.41318"}, 
         {"0.90712", "3.413"}, 
         {"0.90809", "3.41276"}, 
         {"0.90907", "3.4125"}, 
         {"0.91006", "3.4123"}, 
         {"0.91104", "3.41206"}, 
         {"0.91202", "3.4118"}, 
         {"0.913", "3.41158"}, 
         {"0.91398", "3.41139"}, 
         {"0.91496", "3.41109"}, 
         {"0.91594", "3.41081"}, 
         {"0.91693", "3.41055"}, 
         {"0.91791", "3.41025"}, 
         {"0.91889", "3.40996"}, 
         {"0.91986", "3.40963"}, 
         {"0.92084", "3.4093"}, 
         {"0.92182", "3.40889"}, 
         {"0.9228", "3.40858"}, 
         {"0.92378", "3.40822"}, 
         {"0.92477", "3.40787"}, 
         {"0.92575", "3.4075"}, 
         {"0.92673", "3.40712"}, 
         {"0.92771", "3.40671"}, 
         {"0.92869", "3.40628"}, 
         {"0.92967", "3.40587"}, 
         {"0.93064", "3.40544"}, 
         {"0.93163", "3.40495"}, 
         {"0.93261", "3.40446"}, 
         {"0.93359", "3.40387"}, 
         {"0.93457", "3.40324"}, 
         {"0.93555", "3.40263"}, 
         {"0.93653", "3.40198"}, 
         {"0.93751", "3.40127"}, 
         {"0.9385", "3.40052"}, 
         {"0.93948", "3.39977"}, 
         {"0.94046", "3.39886"}, 
         {"0.94144", "3.39797"}, 
         {"0.94241", "3.39702"}, 
         {"0.94339", "3.39593"}, 
         {"0.94437", "3.39488"}, 
         {"0.94535", "3.39376"}, 
         {"0.94634", "3.3925"}, 
         {"0.94732", "3.3911"}, 
         {"0.9483", "3.38955"}, 
         {"0.94928", "3.388"}, 
         {"0.95026", "3.38611"}, 
         {"0.95124", "3.38413"}, 
         {"0.95222", "3.38188"}, 
         {"0.95321", "3.37937"}, 
         {"0.95418", "3.37648"}, 
         {"0.95516", "3.37334"}, 
         {"0.95614", "3.36996"}, 
         {"0.95712", "3.36603"}, 
         {"0.9581", "3.36161"}, 
         {"0.95908", "3.35653"}, 
         {"0.96006", "3.35039"}, 
         {"0.96104", "3.3434"}, 
         {"0.96202", "3.33494"}, 
         {"0.963", "3.32402"}, 
         {"0.96397", "3.31108"}, 
         {"0.96495", "3.29514"}, 
         {"0.96592", "3.27542"}, 
         {"0.9669", "3.2532"}, 
         {"0.96787", "3.2283"}, 
         {"0.96883", "3.20099"}, 
         {"0.96979", "3.17334"}, 
         {"0.97076", "3.14559"}, 
         {"0.97173", "3.1179"}, 
         {"0.9727", "3.09009"}, 
         {"0.97365", "3.06268"}, 
         {"0.97462", "3.03564"}, 
         {"0.97559", "3.00917"}, 
         {"0.97656", "2.98312"}, 
         {"0.97753", "2.95715"}, 
         {"0.97849", "2.93093"}, 
         {"0.97946", "2.90393"}, 
         {"0.98043", "2.87722"}, 
         {"0.9814", "2.85015"}, 
         {"0.98236", "2.82177"}, 
         {"0.98332", "2.79417"}, 
         {"0.98429", "2.76389"}, 
         {"0.98525", "2.73164"}, 
         {"0.98621", "2.69857"}, 
         {"0.98716", "2.66346"}, 
         {"0.98812", "2.62474"}, 
         {"0.98907", "2.58314"}, 
         {"0.99", "2.53564"}});

    return model;
  }

  public static Model run11(Model model) {
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int15")
         .set("interp", "piecewisecubic");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int15")
         .set("extrap", "linear");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int15")
         .set("fununit", new String[]{"V"});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int15")
         .set("argunit", new String[]{"1"});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int16")
         .label("LFPdis1\u4fee\u6b63+\u5e73\u6ed1");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int16")
         .set("funcname", "Eeq_int16");

    return model;
  }

  public static Model run12(Model model) {
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int16")
         .set("table", loadTableFromSnapshot("run12", "int16"));

    return model;
  }
  public static Model run13(Model model) {
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int16")
         .set("extrap", "linear");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int16")
         .set("fununit", new String[]{""});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int17")
         .label("Interpolation 1.2");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int17")
         .set("funcname", "Eeq_int17");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int17")
         .set("table", new String[][]{{"0.01", "3.538446291"}, 
         {"0.02", "3.430533"}, 
         {"0.03", "3.424694609"}, 
         {"0.04", "3.424504348"}, 
         {"0.05", "3.424500072"}, 
         {"0.06", "3.424500001"}, 
         {"0.07", "3.4245"}, 
         {"0.08", "3.4245"}, 
         {"0.09", "3.4245"}, 
         {"0.1", "3.4245"}, 
         {"0.11", "3.4245"}, 
         {"0.12", "3.4245"}, 
         {"0.13", "3.4245"}, 
         {"0.14", "3.4245"}, 
         {"0.15", "3.4245"}, 
         {"0.16", "3.4245"}, 
         {"0.17", "3.4245"}, 
         {"0.18", "3.4245"}, 
         {"0.19", "3.4245"}, 
         {"0.2", "3.4245"}, 
         {"0.21", "3.4245"}, 
         {"0.22", "3.4245"}, 
         {"0.23", "3.4245"}, 
         {"0.24", "3.4245"}, 
         {"0.25", "3.4245"}, 
         {"0.26", "3.4245"}, 
         {"0.27", "3.4245"}, 
         {"0.28", "3.4245"}, 
         {"0.29", "3.4245"}, 
         {"0.3", "3.4245"}, 
         {"0.31", "3.4245"}, 
         {"0.32", "3.4245"}, 
         {"0.33", "3.4245"}, 
         {"0.34", "3.4245"}, 
         {"0.35", "3.4245"}, 
         {"0.36", "3.4245"}, 
         {"0.37", "3.4245"}, 
         {"0.38", "3.4245"}, 
         {"0.39", "3.4245"}, 
         {"0.4", "3.4245"}, 
         {"0.41", "3.4245"}, 
         {"0.42", "3.4245"}, 
         {"0.43", "3.4245"}, 
         {"0.44", "3.4245"}, 
         {"0.45", "3.4245"}, 
         {"0.46", "3.4245"}, 
         {"0.47", "3.4245"}, 
         {"0.48", "3.4245"}, 
         {"0.49", "3.4245"}, 
         {"0.5", "3.4245"}, 
         {"0.51", "3.4245"}, 
         {"0.52", "3.4245"}, 
         {"0.53", "3.4245"}, 
         {"0.54", "3.4245"}, 
         {"0.55", "3.4245"}, 
         {"0.56", "3.4245"}, 
         {"0.57", "3.4245"}, 
         {"0.58", "3.4245"}, 
         {"0.59", "3.4245"}, 
         {"0.6", "3.4245"}, 
         {"0.61", "3.4245"}, 
         {"0.62", "3.4245"}, 
         {"0.63", "3.4245"}, 
         {"0.64", "3.4245"}, 
         {"0.65", "3.4245"}, 
         {"0.66", "3.4245"}, 
         {"0.67", "3.4245"}, 
         {"0.68", "3.4245"}, 
         {"0.69", "3.4245"}, 
         {"0.7", "3.4245"}, 
         {"0.71", "3.4245"}, 
         {"0.72", "3.4245"}, 
         {"0.73", "3.4245"}, 
         {"0.74", "3.4245"}, 
         {"0.75", "3.4245"}, 
         {"0.76", "3.4245"}, 
         {"0.77", "3.4245"}, 
         {"0.78", "3.4245"}, 
         {"0.79", "3.4245"}, 
         {"0.8", "3.424499996"}, 
         {"0.81", "3.424499875"}, 
         {"0.82", "3.424497592"}, 
         {"0.83", "3.424471778"}, 
         {"0.84", "3.424279811"}, 
         {"0.85", "3.423272375"}, 
         {"0.86", "3.419316956"}, 
         {"0.87", "3.407123221"}, 
         {"0.88", "3.376401149"}, 
         {"0.89", "3.311000755"}, 
         {"0.9", "3.190071347"}});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int17")
         .set("interp", "piecewisecubic");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int17")
         .set("extrap", "linear");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int17")
         .set("fununit", new String[]{"V"});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").func("int17")
         .set("argunit", new String[]{""});
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").set("Eeq", "Eeq_int16(soc)");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential")
         .setPropertyInfo("Eeq", "U. S. Kasavajjula, C. Wang, and P. E. Arce, \"Discharge Model for LiFePO4 Accounting for the Solid Solution Range\", J. Electrochemical Soc., vol. 155, p. A866, 2008");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").set("dEeqdT", "dEeqdT_int1(soc)");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential")
         .setPropertyInfo("dEeqdT", "R. E. Gerver and J. P. Meyers, \"Three-Dimensional Modeling of Electrochemical Performance and Heat Generation of Lithium-Ion Betteries in Tabbed Planar Configurations\", J. Electrochemical Soc., vol. 158, p. A835, 2011");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").set("cEeqref", "csmax_pos");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential")
         .setPropertyInfo("cEeqref", "U. S. Kasavajjula, C. Wang, and P. E. Arce, \"Discharge Model for LiFePO4 Accounting for the Solid Solution Range\", J. Electrochemical Soc., vol. 155, p. A866, 2008");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").set("soc", "c/cEeqref");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").descr("soc", "");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").addInput("concentration");
    model.component("comp1").material("mat3").propertyGroup("ElectrodePotential").addInput("temperature");
    model.component("comp1").material("mat3").propertyGroup("OperationalSOC")
         .label("Operational electrode state-of-charge");
    model.component("comp1").material("mat3").propertyGroup("OperationalSOC").set("socmax", "1");
    model.component("comp1").material("mat3").propertyGroup("OperationalSOC").set("socmin", "0");
    model.component("comp1").material("mat3").propertyGroup("ic").label("Intercalation strain");
    model.component("comp1").material("mat3").propertyGroup("ic").set("dvol", "11.62[cm^3/mol]*(c-elpot.cEeqref)");
    model.component("comp1").material("mat3").propertyGroup("ic")
         .setPropertyInfo("dvol", "R. Koerver and others, \u201cChemo-mechanical expansion of lithium electrode materials \u2014 on the route to mechanically optimized all-solid-state batteries,\u201d Energy Environ. Sci., vol. 11, pp. 2142\u20132158, 201");
    model.component("comp1").material("mat3").propertyGroup("ic").addInput("concentration");
    model.component("comp1").material("mat4").label("Aluminum");
    model.component("comp1").material("mat4").set("family", "aluminum");
    model.component("comp1").material("mat4").propertyGroup("def").label("Basic");
    model.component("comp1").material("mat4").propertyGroup("def")
         .set("relpermeability", new String[]{"1", "0", "0", "0", "1", "0", "0", "0", "1"});
    model.component("comp1").material("mat4").propertyGroup("def").set("heatcapacity", "900[J/(kg*K)]");
    model.component("comp1").material("mat4").propertyGroup("def")
         .set("thermalconductivity", new String[]{"238[W/(m*K)]", "0", "0", "0", "238[W/(m*K)]", "0", "0", "0", "238[W/(m*K)]"});
    model.component("comp1").material("mat4").propertyGroup("def")
         .set("electricconductivity", new String[]{"3.774e7[S/m]", "0", "0", "0", "3.774e7[S/m]", "0", "0", "0", "3.774e7[S/m]"});
    model.component("comp1").material("mat4").propertyGroup("def")
         .set("relpermittivity", new String[]{"1", "0", "0", "0", "1", "0", "0", "0", "1"});
    model.component("comp1").material("mat4").propertyGroup("def")
         .set("thermalexpansioncoefficient", new String[]{"23e-6[1/K]", "0", "0", "0", "23e-6[1/K]", "0", "0", "0", "23e-6[1/K]"});
    model.component("comp1").material("mat4").propertyGroup("def").set("density", "2700[kg/m^3]");
    model.component("comp1").material("mat4").propertyGroup("Enu").label("Young's modulus and Poisson's ratio");
    model.component("comp1").material("mat4").propertyGroup("Enu").set("E", "70e9[Pa]");
    model.component("comp1").material("mat4").propertyGroup("Enu").set("nu", "0.33");
    model.component("comp1").material("mat4").propertyGroup("Murnaghan").set("l", "-2.5e11[Pa]");
    model.component("comp1").material("mat4").propertyGroup("Murnaghan").set("m", "-3.3e11[Pa]");
    model.component("comp1").material("mat4").propertyGroup("Murnaghan").set("n", "-3.5e11[Pa]");
    model.component("comp1").material("mat4").propertyGroup("Lame").label("Lam\u00e9 parameters");
    model.component("comp1").material("mat4").propertyGroup("Lame").set("lambLame", "5.1e10[Pa]");
    model.component("comp1").material("mat4").propertyGroup("Lame").set("muLame", "2.6e10[Pa]");
    model.component("comp1").material("mat5").label("Copper");
    model.component("comp1").material("mat5").set("family", "copper");
    model.component("comp1").material("mat5").propertyGroup("def").label("Basic");
    model.component("comp1").material("mat5").propertyGroup("def")
         .set("relpermeability", new String[]{"1", "0", "0", "0", "1", "0", "0", "0", "1"});
    model.component("comp1").material("mat5").propertyGroup("def")
         .set("electricconductivity", new String[]{"5.998e7[S/m]", "0", "0", "0", "5.998e7[S/m]", "0", "0", "0", "5.998e7[S/m]"});
    model.component("comp1").material("mat5").propertyGroup("def")
         .set("thermalexpansioncoefficient", new String[]{"17e-6[1/K]", "0", "0", "0", "17e-6[1/K]", "0", "0", "0", "17e-6[1/K]"});
    model.component("comp1").material("mat5").propertyGroup("def").set("heatcapacity", "385[J/(kg*K)]");
    model.component("comp1").material("mat5").propertyGroup("def")
         .set("relpermittivity", new String[]{"1", "0", "0", "0", "1", "0", "0", "0", "1"});
    model.component("comp1").material("mat5").propertyGroup("def").set("density", "8960[kg/m^3]");
    model.component("comp1").material("mat5").propertyGroup("def")
         .set("thermalconductivity", new String[]{"400[W/(m*K)]", "0", "0", "0", "400[W/(m*K)]", "0", "0", "0", "400[W/(m*K)]"});
    model.component("comp1").material("mat5").propertyGroup("Enu").label("Young's modulus and Poisson's ratio");
    model.component("comp1").material("mat5").propertyGroup("Enu").set("E", "110e9[Pa]");
    model.component("comp1").material("mat5").propertyGroup("Enu").set("nu", "0.35");
    model.component("comp1").material("mat5").propertyGroup("linzRes").label("Linearized resistivity");
    model.component("comp1").material("mat5").propertyGroup("linzRes").set("rho0", "1.72e-8[ohm*m]");
    model.component("comp1").material("mat5").propertyGroup("linzRes").set("alpha", "0.0039[1/K]");
    model.component("comp1").material("mat5").propertyGroup("linzRes").set("Tref", "298[K]");
    model.component("comp1").material("mat5").propertyGroup("linzRes").addInput("temperature");

    model.component("comp1").cpl("intop1").set("opname", "poscc");
    model.component("comp1").cpl("intop2").set("opname", "neg");
    model.component("comp1").cpl("intop3").set("opname", "sep");
    model.component("comp1").cpl("intop4").set("opname", "pos");
    model.component("comp1").cpl("intop5").set("opname", "negcc");
    model.component("comp1").cpl("aveop1").set("opname", "avenegCC");
    model.component("comp1").cpl("aveop2").set("opname", "aveneg");
    model.component("comp1").cpl("aveop3").set("opname", "avesep");
    model.component("comp1").cpl("aveop4").set("opname", "avepos");
    model.component("comp1").cpl("aveop5").set("opname", "aveposCC");
    model.component("comp1").cpl("aveop6").label("\u5e73\u5747\u503c2");
    model.component("comp1").cpl("aveop6").set("opname", "aveop2");

    model.common("cminpt").set("modified", new String[][]{{"temperature", "T"}});

    model.component("comp1").physics("liion").prop("ShapeProperty").set("order_electricpotentialionicphase", 1);
    model.component("comp1").physics("liion").prop("ShapeProperty").set("order_concentration", 1);
    model.component("comp1").physics("liion").prop("ShapeProperty").set("order_electricpotential", 1);
    model.component("comp1").physics("liion").prop("Ac").set("Ac", "Ac");
    model.component("comp1").physics("liion").prop("AdvancedSettings")
         .set("ElectrolyteSaltMaterialBalanceForm", "cons");
    model.component("comp1").physics("liion").feature("ice1").set("minput_temperature_src", "userdef");
    model.component("comp1").physics("liion").feature("ice1").set("minput_temperature", "T");
    model.component("comp1").physics("liion").feature("init1").set("phil", "-mat1.elpot.Eeq_int5(socmin_neg)");
    model.component("comp1").physics("liion").feature("init1").set("cl", "900[mol/m^3]");
    model.component("comp1").physics("liion").feature("init2").set("cl", 0);
    model.component("comp1").physics("liion").feature("init4").set("phil", "-mat1.elpot.Eeq_int5(socmin_neg)");
    model.component("comp1").physics("liion").feature("init4").set("cl", "900[mol/m^3]");
    model.component("comp1").physics("liion").feature("init4").set("phis", 2.8);
    model.component("comp1").physics("liion").feature("init3").set("cl", 0);
    model.component("comp1").physics("liion").feature("init3").set("phis", 2.8);
    model.component("comp1").physics("liion").feature("pce1").set("ElectrolyteMaterial", "mat2");
    model.component("comp1").physics("liion").feature("pce1").set("ElectrodeMaterial", "mat1");
    model.component("comp1").physics("liion").feature("pce1").set("sigma_mat", "from_mat");
    model.component("comp1").physics("liion").feature("pce1")
         .set("sigma", new int[][]{{0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}});
    model.component("comp1").physics("liion").feature("pce1").set("epsl", "epsl_neg");
    model.component("comp1").physics("liion").feature("pce1").set("epss", "epss_neg");
    model.component("comp1").physics("liion").feature("pce1").set("minput_temperature_src", "userdef");
    model.component("comp1").physics("liion").feature("pce1").set("minput_temperature", "T");
    model.component("comp1").physics("liion").feature("pce1").label("neg");
    model.component("comp1").physics("liion").feature("pce1").feature("pin1").set("csinit", "c0_neg");
    model.component("comp1").physics("liion").feature("pce1").feature("pin1").set("Ds_mat", "userdef");
    model.component("comp1").physics("liion").feature("pce1").feature("pin1").set("Ds", "Ds_neg_T");
    model.component("comp1").physics("liion").feature("pce1").feature("pin1").set("ParticleMaterial", "mat1");
    model.component("comp1").physics("liion").feature("pce1").feature("pin1").set("cEeqref_mat", "userdef");
    model.component("comp1").physics("liion").feature("pce1").feature("pin1").set("cEeqref", "csmax_neg");
    model.component("comp1").physics("liion").feature("pce1").feature("pin1").set("rp", "rp_neg");
    model.component("comp1").physics("liion").feature("pce1").feature("per1").set("MaterialOption", "mat1");
    model.component("comp1").physics("liion").feature("pce1").feature("per1").set("Eeq_mat", "userdef");
    model.component("comp1").physics("liion").feature("pce1").feature("per1")
         .set("Eeq", "if(liion.Its_ec1>0,mat1.elpot.Eeq_int5(liion.socloc_average),mat1.elpot.Eeq_int7(liion.socloc_average))");
    model.component("comp1").physics("liion").feature("pce1").feature("per1").set("i0refType", "FromRateConstant");
    model.component("comp1").physics("liion").feature("pce1").feature("per1")
         .set("i0_ref", "ks.neg*exp(Es.kneg/8.314*(1/T_ref-1/T))*F_const*csmax_neg*k_gra");
    model.component("comp1").physics("liion").feature("pce1").feature("per1").set("k", "k_neg_T");
    model.component("comp1").physics("liion").feature("pce2").set("ElectrolyteMaterial", "mat2");
    model.component("comp1").physics("liion").feature("pce2").set("ElectrodeMaterial", "mat3");
    model.component("comp1").physics("liion").feature("pce2").set("sigma_mat", "from_mat");
    model.component("comp1").physics("liion").feature("pce2")
         .set("sigma", new int[][]{{0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}});
    model.component("comp1").physics("liion").feature("pce2").set("epsl", "epsl_pos");
    model.component("comp1").physics("liion").feature("pce2").set("epss", "epss_pos");
    model.component("comp1").physics("liion").feature("pce2").set("minput_temperature_src", "userdef");
    model.component("comp1").physics("liion").feature("pce2").set("minput_temperature", "T");
    model.component("comp1").physics("liion").feature("pce2").label("pos");
    model.component("comp1").physics("liion").feature("pce2").feature("pin1").set("csinit", "c0_pos");
    model.component("comp1").physics("liion").feature("pce2").feature("pin1").set("Ds_mat", "userdef");
    model.component("comp1").physics("liion").feature("pce2").feature("pin1").set("Ds", "Ds_pos_T");
    model.component("comp1").physics("liion").feature("pce2").feature("pin1").set("cEeqref_mat", "userdef");
    model.component("comp1").physics("liion").feature("pce2").feature("pin1").set("cEeqref", "csmax_pos");
    model.component("comp1").physics("liion").feature("pce2").feature("pin1").set("rp", "rp_pos");
    model.component("comp1").physics("liion").feature("pce2").feature("per1").set("Eeq_mat", "userdef");
    model.component("comp1").physics("liion").feature("pce2").feature("per1")
         .set("Eeq", "if(liion.Its_ec1>0,mat3.elpot.Eeq_int15(liion.socloc_average)+0.02,mat3.elpot.Eeq_int15(liion.socloc_average)-0.02)");
    model.component("comp1").physics("liion").feature("pce2").feature("per1").set("i0refType", "FromRateConstant");
    model.component("comp1").physics("liion").feature("pce2").feature("per1")
         .set("i0_ref", "ks.pos*exp(Es.kpos/8.314*(1/T_ref-1/T))*F_const*csmax_pos*k_LFP");
    model.component("comp1").physics("liion").feature("pce2").feature("per1").set("k", "k_pos_T");
    model.component("comp1").physics("liion").feature("pce2").feature("per1").set("ilim", "1e3[A/m^2]");
    model.component("comp1").physics("liion").feature("pce2").feature("per1")
         .set("ExtrapolateInsertionKinetics", false);
    model.component("comp1").physics("liion").feature("ece1").label("\u7535\u6781 1");
    model.component("comp1").physics("liion").feature("sep1").selection().set(3);
    model.component("comp1").physics("liion").feature("sep1").set("ElectrolyteMaterial", "mat2");
    model.component("comp1").physics("liion").feature("sep1").set("epsl", "epsl_sep");
    model.component("comp1").physics("liion").feature("socicd1").label("SOC and Initial Charge Distribution 1");
    model.component("comp1").physics("liion").feature("socicd1").feature("neges1")
         .label("Negative Electrode Selection 1");
    model.component("comp1").physics("liion").feature("socicd1").feature("poses1")
         .label("Positive Electrode Selection 1");
    model.component("comp1").physics("liion").feature("socicd1").feature("negebs1")
         .label("Negative Electrode Boundary Selection 1");
    model.component("comp1").physics("liion").feature("socicd1").feature("posebs1")
         .label("Positive Electrode Boundary Selection 1");
    model.component("comp1").physics("liion").feature("ec1").set("Its", "-i_1C*C*3.2[V]/(comp1.vol)");
    model.component("comp1").physics("liion").feature("ec1").set("phis0init", "3[V]");
    model.component("comp1").physics("liion").feature("ec1").set("IncludeContactResistance", true);
    model.component("comp1").physics("liion").feature("ec1").set("Rc", "0.1[mohm]*Ac");
    model.component("comp1").physics("ge").feature("ge1").set("name", "Q1");
    model.component("comp1").physics("ge").feature("ge1").set("equation", "Q1t-abs(liion.Its_ec1)");
    model.component("comp1").physics("ge").feature("ge1").set("SourceTermQuantity", "none");
    model.component("comp1").physics("ge").feature("ge1").set("CustomSourceTermUnit", "A");
    model.component("comp1").physics("ge").feature("ge2").set("name", "W1");
    model.component("comp1").physics("ge").feature("ge2").set("equation", "W1t-abs(liion.Its_ec1*vol)");
    model.component("comp1").physics("ge").feature("ge2").set("SourceTermQuantity", "none");
    model.component("comp1").physics("ge").feature("ge2").set("CustomSourceTermUnit", "W");
    model.component("comp1").physics("ev").active(false);
    model.component("comp1").physics("ev").feature("ds1")
         .set("dim", new String[][]{{"charge1"}, {"charge2"}, {"charge3"}, {"TimeOfSwitch"}});
    model.component("comp1").physics("ev").feature("ds1").set("dimInit", new int[][]{{1}, {0}, {0}, {0}});
    model.component("comp1").physics("ev").feature("ds1").set("dimDescr", new String[][]{{""}, {""}, {""}, {""}});
    model.component("comp1").physics("ev").feature("is1")
         .set("indDim", new String[][]{{"charge1up"}, {"OkToSwitch"}, {"charge3up"}});
    model.component("comp1").physics("ev").feature("is1")
         .set("g", new String[][]{{"3.65-comp1.cir.vm1.v"}, {"t-TimeOfSwitch-1800[s]"}, {"comp1.cir.vm1.v-2.5"}});
    model.component("comp1").physics("ev").feature("is1").set("dimInit", new int[][]{{0}, {0}, {0}});
    model.component("comp1").physics("ev").feature("is1")
         .set("dimDescr", new String[][]{{""}, {"Ok To Switch?"}, {""}});
    model.component("comp1").physics("ev").feature("impl1").set("condition", "(charge1up<0)");
    model.component("comp1").physics("ev").feature("impl1")
         .set("reInitName", new String[][]{{"charge1"}, {"charge2"}, {"charge3"}, {"TimeOfSwitch"}});
    model.component("comp1").physics("ev").feature("impl1")
         .set("reInitValue", new String[][]{{"0"}, {"1"}, {"0"}, {"root.t"}});
    model.component("comp1").physics("ev").feature("impl2").set("condition", "(OkToSwitch>0)&&(charge1==0)");
    model.component("comp1").physics("ev").feature("impl2")
         .set("reInitName", new String[][]{{"charge1"}, {"charge2"}, {"charge3"}});
    model.component("comp1").physics("ev").feature("impl2").set("reInitValue", new int[][]{{0}, {0}, {1}});
    model.component("comp1").physics("ev").feature("impl3").set("condition", "(charge3up<0)");
    model.component("comp1").physics("ev").feature("impl3")
         .set("reInitName", new String[][]{{"charge1"}, {"charge2"}, {"charge3"}});
    model.component("comp1").physics("ev").feature("impl3").set("reInitValue", new int[][]{{1}, {0}, {0}});
    model.component("comp1").physics("ev").feature("ds2").set("dim", new String[][]{{"charge3"}, {"TimeOfSwitch"}});
    model.component("comp1").physics("ev").feature("ds2").set("dimInit", new int[][]{{0}, {-1800}});
    model.component("comp1").physics("ev").feature("ds2").set("dimDescr", new String[][]{{""}, {""}});
    model.component("comp1").physics("ev").feature("is2").set("indDim", "OkToSwitch");
    model.component("comp1").physics("ev").feature("is2").set("g", "t-TimeOfSwitch-1800[s]");
    model.component("comp1").physics("ev").feature("is2").set("dimInit", 0);
    model.component("comp1").physics("ev").feature("is2").set("dimDescr", "Ok To Switch?");

    model.component("comp1").mesh("mesh1").feature("edg2").feature("size1").set("hauto", 1);
    model.component("comp1").mesh("mesh1").feature("edg2").feature("size1").set("custom", "on");
    model.component("comp1").mesh("mesh1").feature("edg2").feature("size1").set("hmax", "1.64E-6*2");
    model.component("comp1").mesh("mesh1").feature("edg2").feature("size1").set("hmaxactive", true);
    model.component("comp1").mesh("mesh1").feature("edg2").feature("size1").set("hmin", 3.28E-9);
    model.component("comp1").mesh("mesh1").feature("edg2").feature("size1").set("hminactive", false);
    model.component("comp1").mesh("mesh1").run();

    model.component("comp1").probe("point1").set("probename", "vol");
    model.component("comp1").probe("point1").set("expr", "liion.phis0_ec1");
    model.component("comp1").probe("point1").set("descr", "\u8fb9\u754c\u7535\u4f4d");
    model.component("comp1").probe("point1").set("table", "tbl10");
    model.component("comp1").probe("point1").set("window", "window4");
    model.component("comp1").probe("point1").selection().set(6);
    model.component("comp1").probe("var1").label("Q2");
    model.component("comp1").probe("var1").set("expr", "-Q2");
    model.component("comp1").probe("var1").set("unit", "Ah");
    model.component("comp1").probe("var1").set("descr", "-Q2");
    model.component("comp1").probe("var1").set("table", "tbl10");
    model.component("comp1").probe("var1").set("window", "window11");
    model.component("comp1").probe("point2").label("Ect");
    model.component("comp1").probe("point2").set("expr", "liion.Ect");
    model.component("comp1").probe("point2").set("descr", "\u7535\u6781\u7535\u4f4d");
    model.component("comp1").probe("point2").set("table", "tbl10");
    model.component("comp1").probe("point2").set("window", "window10");
    model.component("comp1").probe("point2").selection().set(3);

    model.study().create("std1");
    model.study("std1").create("param", "Parametric");
    model.study("std1").create("param2", "Parametric");
    model.study("std1").create("param3", "Parametric");
    model.study("std1").create("time", "Transient");

    model.batch().create("p1", "Parametric");
    model.batch().create("p2", "Parametric");
    model.batch().create("p3", "Parametric");
    model.batch().create("p4", "Parametric");
    model.batch().create("p5", "Parametric");
    model.batch().create("p6", "Parametric");
    model.batch().create("p7", "Parametric");
    model.batch("p1").create("so1", "Solutionseq");
    model.batch("p2").create("so1", "Solutionseq");
    model.batch("p3").create("jo1", "Jobseq");
    model.batch("p4").create("so1", "Solutionseq");
    model.batch("p5").create("so1", "Solutionseq");
    model.batch("p6").create("jo1", "Jobseq");
    model.batch("p7").create("jo1", "Jobseq");
    model.batch("p1").study("std1");
    model.batch("p2").study("std1");
    model.batch("p3").study("std1");
    model.batch("p4").study("std1");
    model.batch("p5").study("std1");
    model.batch("p6").study("std1");
    model.batch("p7").study("std1");

    model.sol().create("sol5");
    model.sol("sol5").attach("std1");
    model.sol("sol5").create("st1", "StudyStep");
    model.sol("sol5").create("v1", "Variables");
    model.sol("sol5").create("t1", "Time");
    model.sol("sol5").feature("t1").create("fc1", "FullyCoupled");
    model.sol("sol5").feature("t1").create("d1", "Direct");
    model.sol("sol5").feature("t1").create("i1", "Iterative");
    model.sol("sol5").feature("t1").create("i2", "Iterative");
    model.sol("sol5").feature("t1").create("st1", "StopCondition");
    model.sol("sol5").feature("t1").feature("i1").create("mg1", "Multigrid");
    model.sol("sol5").feature("t1").feature("i1").feature("mg1").feature("pr").create("sc1", "SCGS");
    model.sol("sol5").feature("t1").feature("i1").feature("mg1").feature("po").create("sc1", "SCGS");
    model.sol("sol5").feature("t1").feature("i1").feature("mg1").feature("cs").create("d1", "Direct");
    model.sol("sol5").feature("t1").feature("i2").create("mg1", "Multigrid");
    model.sol("sol5").feature("t1").feature("i2").feature("mg1").feature("pr").create("sc1", "SCGS");
    model.sol("sol5").feature("t1").feature("i2").feature("mg1").feature("po").create("sc1", "SCGS");
    model.sol("sol5").feature("t1").feature("i2").feature("mg1").feature("cs").create("d1", "Direct");
    model.sol("sol5").feature("t1").feature().remove("fcDef");
    model.sol().create("sol6");
    model.sol("sol6").study("std1");
    model.sol("sol6").label("\u53c2\u6570\u5316\u89e3 3");
    model.sol().create("sol32");
    model.sol("sol32").study("std1");
    model.sol("sol32").label("DP\u6781\u5316\u5206\u89e3");
    model.sol().create("sol45");
    model.sol("sol45").study("std1");
    model.sol("sol45").label("CP\u6781\u5316\u5206\u89e3");
    model.sol().create("sol56");
    model.sol("sol56").study("std1");
    model.sol("sol56").label("\u53c2\u6570\u5316\u89e3 3 - \u590d\u5236 1");

    model.result().dataset().create("dset6", "Solution");
    model.result().dataset().create("dset7", "Solution");
    model.result().dataset().create("avh1", "Average");
    model.result().dataset().create("avh2", "Average");
    model.result().dataset().create("dset9", "Solution");
    model.result().dataset().create("dset10", "Solution");
    model.result().dataset().create("dset11", "Solution");
    model.result().dataset("dset5").set("solution", "sol5");
    model.result().dataset("dset6").set("solution", "sol6");
    model.result().dataset("dset7").set("probetag", "point2");
    model.result().dataset("avh1").set("probetag", "point1");
    model.result().dataset("avh1").set("data", "dset7");
    model.result().dataset("avh1").selection().geom("geom1", 0);
    model.result().dataset("avh1").selection().set(6);
    model.result().dataset("avh2").set("probetag", "point2");
    model.result().dataset("avh2").set("data", "dset7");
    model.result().dataset("avh2").selection().geom("geom1", 0);
    model.result().dataset("avh2").selection().set(3);
    model.result().dataset("dset9").set("solution", "sol32");
    model.result().dataset("dset10").set("solution", "sol45");
    model.result().dataset("dset11").set("solution", "sol56");
    model.result().dataset().remove("dset1");
    model.result().dataset().remove("dset2");
    model.result().dataset().remove("dset3");
    model.result().dataset().remove("dset4");
    model.result().numerical().create("pev1", "EvalPoint");
    model.result().numerical().create("gev1", "EvalGlobal");
    model.result().numerical().create("pev2", "EvalPoint");
    model.result().numerical().create("gev2", "EvalGlobal");
    model.result().numerical("pev1").set("probetag", "point1");
    model.result().numerical("gev1").set("data", "dset7");
    model.result().numerical("gev1").set("probetag", "var1");
    model.result().numerical("pev2").set("probetag", "point2");
    model.result().numerical("gev2").set("data", "dset9");
    model.result().create("pg100", "PlotGroup1D");
    model.result().create("pg166", "PlotGroup1D");
    model.result().create("pg157", "PlotGroup1D");
    model.result().create("pg179", "PlotGroup1D");
    model.result().create("pg182", "PlotGroup1D");
    model.result().create("pg184", "PlotGroup1D");
    model.result().create("pg183", "PlotGroup1D");
    model.result().create("pg186", "PlotGroup1D");
    model.result().create("pg187", "PlotGroup1D");
    model.result().create("pg188", "PlotGroup1D");
    model.result("pg100").set("probetag", "window4");
    model.result("pg100").create("tblp1", "Table");
    model.result("pg100").feature("tblp1").set("probetag", "point1");
    model.result("pg166").create("tblp2", "Table");
    model.result("pg166").create("tblp3", "Table");
    model.result("pg166").create("tblp4", "Table");
    model.result("pg166").create("tblp5", "Table");
    model.result("pg166").create("tblp6", "Table");
    model.result("pg157").set("probetag", "window10");
    model.result("pg157").create("tblp1", "Table");
    model.result("pg157").create("tblp2", "Table");
    model.result("pg157").feature("tblp1").set("probetag", "point2");
    model.result("pg179").set("probetag", "window11");
    model.result("pg179").create("tblp3", "Table");
    model.result("pg179").feature("tblp3").set("probetag", "VoltMeter_cir_vm1,var1");
    model.result("pg182").create("tblp1", "Table");
    model.result("pg182").create("tblp2", "Table");
    model.result("pg182").create("tblp3", "Table");
    model.result("pg182").create("tblp4", "Table");
    model.result("pg182").create("tblp5", "Table");
    model.result("pg182").create("tblp6", "Table");
    model.result("pg182").create("glob1", "Global");
    model.result("pg182").create("glob2", "Global");
    model.result("pg182").feature("glob1").set("data", "dset6");
    model.result("pg182").feature("glob1").set("expr", new String[]{"vol"});
    model.result("pg182").feature("glob2").set("data", "dset9");

    return model;
  }

  public static Model run14(Model model) {
    model.result("pg182").feature("glob2").set("expr", new String[]{"vol"});
    model.result("pg184").create("tblp1", "Table");
    model.result("pg184").create("tblp3", "Table");
    model.result("pg184").create("tblp5", "Table");
    model.result("pg184").create("tblp2", "Table");
    model.result("pg184").create("tblp4", "Table");
    model.result("pg184").create("tblp6", "Table");
    model.result("pg183").create("glob3", "Global");
    model.result("pg183").feature("glob3").set("data", "dset6");
    model.result("pg183").feature("glob3").set("expr", new String[]{"comp1.cir.vm1.v", ""});
    model.result("pg186").set("probetag", "window10");
    model.result("pg186").create("tblp1", "Table");
    model.result("pg186").feature("tblp1").set("probetag", "point2");
    model.result("pg187").set("data", "dset9");
    model.result("pg187").create("glob1", "Global");
    model.result("pg187").create("glob2", "Global");
    model.result("pg187").feature("glob1").set("expr", new String[]{"total/liion.Its_ec1"});
    model.result("pg187").feature("glob2")
         .set("expr", new String[]{"total_neg/liion.Its_ec1", "total_pos/liion.Its_ec1", "total_sep/liion.Its_ec1"});
    model.result("pg188").set("data", "dset6");
    model.result("pg188").create("glob1", "Global");
    model.result("pg188").create("glob2", "Global");
    model.result("pg188").create("ptgr1", "PointGraph");
    model.result("pg188").feature("glob1").set("expr", new String[]{"abs(total/liion.Its_ec1)"});
    model.result("pg188").feature("glob2")
         .set("expr", new String[]{"abs(ohms/liion.Its_ec1)", "abs(ohml/liion.Its_ec1)", "abs(dl/liion.Its_ec1)", "abs(ds/liion.Its_ec1)", "abs(RCT/liion.Its_ec1)"});
    model.result("pg188").feature("ptgr1").selection().set(6);
    model.result("pg188").feature("ptgr1").set("expr", "liion.phis0_ec1");
    model.result().export().create("img1", "Image");

    model.component("comp1").probe("point1").genResult(null);

    model.result("pg189").tag("pg100");

    model.component("comp1").probe("var1").genResult(null);
    model.component("comp1").probe("point2").genResult(null);

    model.nodeGroup().create("grp1", "Definitions", "comp1");
    model.nodeGroup("grp1").placeAfter(null);

    model.study("std1").feature("param3").label("\u8bbe\u8ba1\u53c2\u6570");
    model.study("std1").feature("param3").set("pname", new String[]{"L_neg", "L_pos", "den_neg", "den_pos"});
    model.study("std1").feature("param3")
         .set("plistarr", new String[]{"85.85414193 111.482244", "100.7360689 131.6525095", "0.130498296 0.169453011", "0.253854894 0.331764324"});
    model.study("std1").feature("param3").set("punit", new String[]{"um", "um", "mg/mm^2", "mg/mm^2"});
    model.study("std1").feature("param2").set("pname", new String[]{"SOC"});
    model.study("std1").feature("param2").set("plistarr", new int[]{0});
    model.study("std1").feature("param2").set("punit", new String[]{""});
    model.study("std1").feature("param").set("sweeptype", "filled");
    model.study("std1").feature("param").set("pname", new String[]{"T", "C"});
    model.study("std1").feature("param").set("plistarr", new String[]{"25", ".25"});
    model.study("std1").feature("param").set("punit", new String[]{"degC", ""});
    model.study("std1").feature("param").set("paramselect", false);
    model.study("std1").feature("time").set("tlist", "range(0,20/C,20000/C)");
    model.study("std1").setStoreSolution(true);

    model.batch("p1").set("pname", new String[]{"Ds_neg", "Ds_pos", "k_neg", "k_pos"});
    model.batch("p1").set("plistarr", new String[]{"0.028000000000000004", "0.943", "150.0[C/kg]"});
    model.batch("p1").set("punit", new String[]{"m^2/s", "m^2/s", "m/s", "m/s"});
    model.batch("p1").set("err", true);
    model.batch("p1").feature("so1").set("store", true);
    model.batch("p1").feature("so1").set("clear", "clearforvalue");
    model.batch("p1").run();
    model.batch("p2").set("pname", new String[]{"Ds_neg", "Ds_pos", "k_neg", "k_pos"});
    model.batch("p2")
         .set("plistarr", new String[]{"0.013641", "0.948", "1.0E-11[m^2/s]", "2.4E-16[m^2/s]", "1.2121E-9[m/s]", "1.1131E-10[m/s]"});
    model.batch("p2").set("punit", new String[]{"m^2/s", "m^2/s", "m/s", "m/s", "m/s", "m/s"});
    model.batch("p2").set("err", true);
    model.batch("p2").feature("so1").set("store", true);
    model.batch("p2").feature("so1").set("clear", "clearforvalue");
    model.batch("p2").feature("so1")
         .set("param", new String[]{"\"socini_neg\",\"0.013641\",\"socini_pos\",\"0.948\",\"Ds_neg\",\"1E-11\",\"Ds_pos\",\"2.4E-16\",\"k_neg\",\"1.2121E-9\",\"k_pos\",\"1.1131E-10\""});
    model.batch("p2").run();
    model.batch("p3").set("control", "param");
    model.batch("p3").set("sweeptype", "filled");
    model.batch("p3").set("pname", new String[]{"T", "C"});
    model.batch("p3").set("plistarr", new String[]{"25", ".25"});
    model.batch("p3").set("punit", new String[]{"degC", ""});
    model.batch("p3").set("err", true);
    model.batch("p3").run();
    model.batch("p4").set("control", "param");
    model.batch("p4").set("sweeptype", "filled");
    model.batch("p4").set("pname", new String[]{"T", "C"});
    model.batch("p4").set("plistarr", new String[]{"25", ".25"});
    model.batch("p4").set("punit", new String[]{"degC", ""});
    model.batch("p4").set("err", true);
    model.batch("p4").run();
    model.batch("p5").set("control", "param");
    model.batch("p5").set("sweeptype", "filled");
    model.batch("p5").set("pname", new String[]{"T", "C"});
    model.batch("p5").set("plistarr", new String[]{"25", ".25"});
    model.batch("p5").set("punit", new String[]{"degC", ""});
    model.batch("p5").set("err", true);
    model.batch("p5").feature("so1").set("seq", "sol5");
    model.batch("p5").feature("so1").set("psol", "sol6");
    model.batch("p5").feature("so1")
         .set("param", new String[]{"\"L_neg\",\"8.585414193E-5\",\"L_pos\",\"1.007360689E-4\",\"den_neg\",\"0.130498296\",\"den_pos\",\"0.253854894\",\"SOC\",\"0\",\"T\",\"298.15\",\"C\",\"0.125\"", "\"L_neg\",\"8.585414193E-5\",\"L_pos\",\"1.007360689E-4\",\"den_neg\",\"0.130498296\",\"den_pos\",\"0.253854894\",\"SOC\",\"0\",\"T\",\"298.15\",\"C\",\"0.25\"", "\"L_neg\",\"1.11482244E-4\",\"L_pos\",\"1.316525095E-4\",\"den_neg\",\"0.169453011\",\"den_pos\",\"0.331764324\",\"SOC\",\"0\",\"T\",\"298.15\",\"C\",\"0.125\"", "\"L_neg\",\"1.11482244E-4\",\"L_pos\",\"1.316525095E-4\",\"den_neg\",\"0.169453011\",\"den_pos\",\"0.331764324\",\"SOC\",\"0\",\"T\",\"298.15\",\"C\",\"0.25\""});
    model.batch("p5").attach("std1");
    model.batch("p6").set("control", "param2");
    model.batch("p6").set("pname", new String[]{"SOC"});
    model.batch("p6").set("plistarr", new int[]{0});
    model.batch("p6").set("punit", new String[]{""});
    model.batch("p6").set("err", true);
    model.batch("p6").set("control", "param2");
    model.batch("p6").feature("jo1").set("seq", "p5");
    model.batch("p6").attach("std1");
    model.batch("p7").set("control", "param3");
    model.batch("p7").set("pname", new String[]{"L_neg", "L_pos", "den_neg", "den_pos"});
    model.batch("p7")
         .set("plistarr", new String[]{"85.85414193 111.482244", "100.7360689 131.6525095", "0.130498296 0.169453011", "0.253854894 0.331764324"});
    model.batch("p7").set("punit", new String[]{"um", "um", "mg/mm^2", "mg/mm^2"});
    model.batch("p7").set("err", true);
    model.batch("p7").feature("jo1").set("seq", "p6");
    model.batch("p7").attach("std1");

    model.sol("sol5").feature("st1").label("\u7f16\u8bd1\u65b9\u7a0b: \u77ac\u6001");
    model.sol("sol5").feature("v1").label("\u56e0\u53d8\u91cf 1.1");
    model.sol("sol5").feature("v1").set("resscalemethod", "manual");
    model.sol("sol5").feature("v1").set("clist", new String[]{"{range(0, 20/C, 20000/C)}[s]", "0.001[s]"});
    model.sol("sol5").feature("v1").feature("comp1_cl").set("scalemethod", "manual");
    model.sol("sol5").feature("v1").feature("comp1_cl").set("scaleval", 1000);
    model.sol("sol5").feature("v1").feature("comp1_liion_pce1_cs").set("scalemethod", "manual");
    model.sol("sol5").feature("v1").feature("comp1_liion_pce1_cs").set("scaleval", 10000);
    model.sol("sol5").feature("v1").feature("comp1_liion_pce2_cs").set("scalemethod", "manual");
    model.sol("sol5").feature("v1").feature("comp1_liion_pce2_cs").set("scaleval", 10000);
    model.sol("sol5").feature("v1").feature("comp1_phil").set("scalemethod", "manual");
    model.sol("sol5").feature("v1").feature("comp1_phil").set("scaleval", 1);
    model.sol("sol5").feature("v1").feature("comp1_phis").set("scalemethod", "manual");
    model.sol("sol5").feature("v1").feature("comp1_phis").set("scaleval", 1);
    model.sol("sol5").feature("t1").label("\u77ac\u6001\u6c42\u89e3\u5668 1.1");
    model.sol("sol5").feature("t1").set("tlist", "range(0,20/C,20000/C)");
    model.sol("sol5").feature("t1").set("rtol", 0.001);
    model.sol("sol5").feature("t1").set("initialstepbdfactive", true);
    model.sol("sol5").feature("t1").set("maxorder", 2);
    model.sol("sol5").feature("t1").set("eventout", true);
    model.sol("sol5").feature("t1").feature("dDef").label("\u76f4\u63a5 2");
    model.sol("sol5").feature("t1").feature("aDef").label("\u9ad8\u7ea7 1");
    model.sol("sol5").feature("t1").feature("aDef").set("cachepattern", true);
    model.sol("sol5").feature("t1").feature("fc1").label("\u5168\u8026\u5408 1.1");
    model.sol("sol5").feature("t1").feature("fc1").set("linsolver", "d1");
    model.sol("sol5").feature("t1").feature("fc1").set("dtech", "auto");
    model.sol("sol5").feature("t1").feature("d1").label("\u76f4\u63a5 1.1");
    model.sol("sol5").feature("t1").feature("i1").label("\u4ee3\u6570\u591a\u91cd\u7f51\u683c (liion)");
    model.sol("sol5").feature("t1").feature("i1").set("maxlinit", 1000);
    model.sol("sol5").feature("t1").feature("i1").feature("ilDef").label("\u4e0d\u5b8c\u5168 LU \u5206\u89e3 1");
    model.sol("sol5").feature("t1").feature("i1").feature("mg1").label("\u591a\u91cd\u7f51\u683c 1.1");
    model.sol("sol5").feature("t1").feature("i1").feature("mg1").set("prefun", "saamg");
    model.sol("sol5").feature("t1").feature("i1").feature("mg1").set("maxcoarsedof", 50000);
    model.sol("sol5").feature("t1").feature("i1").feature("mg1").feature("pr").label("\u9884\u5e73\u6ed1\u5668 1");
    model.sol("sol5").feature("t1").feature("i1").feature("mg1").feature("pr").feature("soDef").label("SOR 1");
    model.sol("sol5").feature("t1").feature("i1").feature("mg1").feature("pr").feature("sc1").label("SCGS 1.1");
    model.sol("sol5").feature("t1").feature("i1").feature("mg1").feature("po").label("\u540e\u5e73\u6ed1\u5668 1");
    model.sol("sol5").feature("t1").feature("i1").feature("mg1").feature("po").feature("soDef").label("SOR 1");
    model.sol("sol5").feature("t1").feature("i1").feature("mg1").feature("po").feature("sc1").label("SCGS 1.1");
    model.sol("sol5").feature("t1").feature("i1").feature("mg1").feature("cs")
         .label("\u7c97\u5316\u6c42\u89e3\u5668 1");
    model.sol("sol5").feature("t1").feature("i1").feature("mg1").feature("cs").feature("dDef")
         .label("\u76f4\u63a5 2");
    model.sol("sol5").feature("t1").feature("i1").feature("mg1").feature("cs").feature("d1")
         .label("\u76f4\u63a5 1.1");
    model.sol("sol5").feature("t1").feature("i1").feature("mg1").feature("cs").feature("d1")
         .set("linsolver", "pardiso");
    model.sol("sol5").feature("t1").feature("i2").label("\u51e0\u4f55\u591a\u91cd\u7f51\u683c (liion)");
    model.sol("sol5").feature("t1").feature("i2").set("maxlinit", 1000);
    model.sol("sol5").feature("t1").feature("i2").feature("ilDef").label("\u4e0d\u5b8c\u5168 LU \u5206\u89e3 1");
    model.sol("sol5").feature("t1").feature("i2").feature("mg1").label("\u591a\u91cd\u7f51\u683c 1.1");
    model.sol("sol5").feature("t1").feature("i2").feature("mg1").feature("pr").label("\u9884\u5e73\u6ed1\u5668 1");
    model.sol("sol5").feature("t1").feature("i2").feature("mg1").feature("pr").feature("soDef").label("SOR 1");
    model.sol("sol5").feature("t1").feature("i2").feature("mg1").feature("pr").feature("sc1").label("SCGS 1.1");
    model.sol("sol5").feature("t1").feature("i2").feature("mg1").feature("po").label("\u540e\u5e73\u6ed1\u5668 1");
    model.sol("sol5").feature("t1").feature("i2").feature("mg1").feature("po").feature("soDef").label("SOR 1");
    model.sol("sol5").feature("t1").feature("i2").feature("mg1").feature("po").feature("sc1").label("SCGS 1.1");
    model.sol("sol5").feature("t1").feature("i2").feature("mg1").feature("cs")
         .label("\u7c97\u5316\u6c42\u89e3\u5668 1");
    model.sol("sol5").feature("t1").feature("i2").feature("mg1").feature("cs").feature("dDef")
         .label("\u76f4\u63a5 2");
    model.sol("sol5").feature("t1").feature("i2").feature("mg1").feature("cs").feature("d1")
         .label("\u76f4\u63a5 1.1");
    model.sol("sol5").feature("t1").feature("i2").feature("mg1").feature("cs").feature("d1")
         .set("linsolver", "pardiso");
    model.sol("sol5").feature("t1").feature("st1").label("\u505c\u6b62\u6761\u4ef6 1.1");
    model.sol("sol5").feature("t1").feature("st1").set("stopcondterminateon", new String[]{"true", "true"});
    model.sol("sol5").feature("t1").feature("st1").set("stopcondActive", new String[]{"off", "on"});
    model.sol("sol5").feature("t1").feature("st1")
         .set("stopconddesc", new String[]{"\u505c\u6b62\u8868\u8fbe\u5f0f 1", "\u505c\u6b62\u8868\u8fbe\u5f0f 2"});
    model.sol("sol5").feature("t1").feature("st1")
         .set("stopcondarr", new String[]{"comp1.vol>3.65", "comp1.vol<2.5"});

    model.study("std1").runNoGen();

    model.result().dataset("dset5").set("frametype", "spatial");
    model.result().dataset("dset6").set("frametype", "spatial");
    model.result().dataset("dset7").label("\u63a2\u9488\u89e3 7");
    model.result().numerical("gev2").set("looplevelinput", new String[]{"manualindices", "manual", "manual"});
    model.result().numerical("gev2").set("looplevel", new String[]{"", "3", "1"});
    model.result().numerical("gev2").set("looplevelindices", new String[]{"106", "", ""});
    model.result().numerical("gev2").set("table", "tbl30");
    model.result().numerical("gev2")
         .set("expr", new String[]{"total_neg/liion.Its_ec1", "total_pos/liion.Its_ec1", "total_sep/liion.Its_ec1", "ohms/liion.Its_ec1", "ohml/liion.Its_ec1", "ds/liion.Its_ec1", "dl/liion.Its_ec1", "RCT/liion.Its_ec1", "total/liion.Its_ec1", "ohms_neg/liion.Its_ec1", 
         "ohms_pos/liion.Its_ec1", "ohml_neg/liion.Its_ec1", "ohml_sep/liion.Its_ec1", "ohml_pos/liion.Its_ec1", "ds_neg/liion.Its_ec1", "ds_pos/liion.Its_ec1", "dl_neg/liion.Its_ec1", "dl_sep/liion.Its_ec1", "dl_pos/liion.Its_ec1", "RCT_neg/liion.Its_ec1", 
         "RCT_pos/liion.Its_ec1"});
    model.result().numerical("gev2")
         .set("unit", new String[]{"m\u03a9", "m\u03a9", "m\u03a9", "m\u03a9", "m\u03a9", "m\u03a9", "m\u03a9", "m\u03a9", "m\u03a9", "m\u03a9", 
         "m\u03a9", "m\u03a9", "m\u03a9", "m\u03a9", "m\u03a9", "m\u03a9", "m\u03a9", "m\u03a9", "m\u03a9", "m\u03a9", 
         "m\u03a9"});
    model.result().numerical("gev2")
         .set("descr", new String[]{"\u8d1f\u6781", "\u6b63\u6781", "\u9694\u819c", "\u56fa\u76f8\u6b27\u59c6", "\u6db2\u76f8\u6b27\u59c6", "\u56fa\u76f8\u6269\u6563", "\u6db2\u76f8\u6269\u6563", "\u7535\u8377\u8f6c\u79fb", "\u603b", "\u56fa\u76f8\u6b27\u59c6-\u8d1f\u6781", 
         "\u56fa\u76f8\u6b27\u59c6-\u6b63\u6781", "\u6db2\u76f8\u6b27\u59c6-\u8d1f\u6781", "\u6db2\u76f8\u6b27\u59c6-\u9694\u819c", "\u6db2\u76f8\u6b27\u59c6-\u6b63\u6781", "\u56fa\u76f8\u6269\u6563-\u8d1f\u6781", "\u56fa\u76f8\u6269\u6563-\u6b63\u6781", "\u6db2\u76f8\u6269\u6563-\u8d1f\u6781", "\u6db2\u76f8\u6269\u6563-\u9694\u819c", "\u6db2\u76f8\u6269\u6563-\u6b63\u6781", "\u7535\u8377\u8f6c\u79fb-\u8d1f\u6781", 
         "\u7535\u8377\u8f6c\u79fb-\u6b63\u6781"});
    model.result().numerical("gev2").setResult();
    model.result().create("pg186", "PlotGroup1D");
    model.result("pg100").label("\u63a2\u9488\u7ed8\u56fe\u7ec4 100");
    model.result("pg100").set("solrepresentation", "solnum");
    model.result("pg100").set("xlabel", "\u65f6\u95f4 (s)");
    model.result("pg100").set("ylabel", "\u8fb9\u754c\u7535\u4f4d (V), \u70b9\u63a2\u9488 1");
    model.result("pg100").set("smooth", "internal");
    model.result("pg100").set("windowtitle", "\u63a2\u9488\u56fe\u201c4\u201d");
    model.result("pg100").set("xlabelactive", false);
    model.result("pg100").set("ylabelactive", false);
    model.result("pg166").active(false);
    model.result("pg166").label("\u80fd\u6548");
    model.result("pg166").set("data", "none");
    model.result("pg166").set("solrepresentation", "solnum");
    model.result("pg166").set("manualgrid", true);
    model.result("pg166").set("xspacing", 60);
    model.result("pg166").set("yspacing", ".2");
    model.result("pg166").set("legendpos", "lowerright");
    model.result("pg166").set("smooth", "internal");
    model.result("pg166").feature("tblp2").label("0.25");
    model.result("pg166").feature("tblp2").set("table", "tbl12");
    model.result("pg166").feature("tblp2").set("xaxisdata", 1);
    model.result("pg166").feature("tblp2").set("plotcolumninput", "manual");
    model.result("pg166").feature("tblp2").set("linestyle", "dashed");
    model.result("pg166").feature("tblp2").set("linecolor", "cyclereset");
    model.result("pg166").feature("tblp2").set("linewidth", 2);
    model.result("pg166").feature("tblp2").set("linewidthslider", 2);
    model.result("pg166").feature("tblp3").label("0.33");
    model.result("pg166").feature("tblp3").set("table", "tbl12");
    model.result("pg166").feature("tblp3").set("xaxisdata", 3);
    model.result("pg166").feature("tblp3").set("plotcolumninput", "manual");
    model.result("pg166").feature("tblp3").set("linestyle", "dashed");
    model.result("pg166").feature("tblp3").set("linewidth", 2);
    model.result("pg166").feature("tblp3").set("linewidthslider", 2);
    model.result("pg166").feature("tblp4").label(".5");
    model.result("pg166").feature("tblp4").set("table", "tbl12");
    model.result("pg166").feature("tblp4").set("xaxisdata", 5);
    model.result("pg166").feature("tblp4").set("plotcolumninput", "manual");
    model.result("pg166").feature("tblp4").set("linestyle", "dashed");
    model.result("pg166").feature("tblp4").set("linewidth", 2);
    model.result("pg166").feature("tblp4").set("linewidthslider", 2);
    model.result("pg166").feature("tblp5").label("1");
    model.result("pg166").feature("tblp5").set("table", "tbl12");
    model.result("pg166").feature("tblp5").set("xaxisdata", 7);
    model.result("pg166").feature("tblp5").set("plotcolumninput", "manual");
    model.result("pg166").feature("tblp5").set("linestyle", "dashed");
    model.result("pg166").feature("tblp5").set("linewidth", 2);
    model.result("pg166").feature("tblp5").set("linewidthslider", 2);
    model.result("pg166").feature("tblp6").label("2");
    model.result("pg166").feature("tblp6").set("table", "tbl12");
    model.result("pg166").feature("tblp6").set("xaxisdata", 9);
    model.result("pg166").feature("tblp6").set("plotcolumninput", "manual");
    model.result("pg166").feature("tblp6").set("linestyle", "dashed");
    model.result("pg166").feature("tblp6").set("linewidth", 2);
    model.result("pg166").feature("tblp6").set("linewidthslider", 2);
    model.result("pg157").active(false);
    model.result("pg157").label("\u7535\u538b");
    model.result("pg157").set("twoyaxes", true);
    model.result("pg157")
         .set("plotonsecyaxis", new String[][]{{"\u63a2\u9488\u8868\u56fe 1", "on", "tblp1"}, {"\u63a2\u9488\u8868\u56fe 1.1", "off", "tblp2"}});
    model.result("pg157").set("smooth", "internal");
    model.result("pg157").set("windowtitle", "\u63a2\u9488\u56fe\u201c10\u201d");
    model.result("pg157").create("tblp1", "Table");
    model.result("pg157").feature("tblp1").label("\u63a2\u9488\u8868\u56fe 1");
    model.result("pg157").feature("tblp1").set("plotcolumninput", "manual");
    model.result("pg157").feature("tblp1").set("plotonsecyaxis", true);
    model.result("pg157").feature("tblp1").set("legend", true);
    model.result("pg157").feature("tblp2").label("\u63a2\u9488\u8868\u56fe 1.1");
    model.result("pg157").feature("tblp2").set("plotcolumninput", "manual");
    model.result("pg157").feature("tblp2").set("legend", true);
    model.result("pg157").feature().remove("tblp3");
    model.result("pg179").label("\u63a2\u9488");
    model.result("pg179").set("smooth", "internal");
    model.result("pg179").set("windowtitle", "\u63a2\u9488\u56fe\u201c11\u201d");
    model.result("pg179").feature("tblp3").label("\u63a2\u9488\u8868\u56fe 3");
    model.result("pg179").feature("tblp3").set("linemarker", "star");
    model.result("pg179").feature("tblp3").set("legend", true);
    model.result("pg182").label("\u8f6f\u53050.5~2P\u5145\u653e");
    model.result("pg182").set("data", "none");
    model.result("pg182").set("titletype", "manual");
    model.result("pg182").set("title", "Simulated charge curve of pouch battery @25\u2103");
    model.result("pg182").set("xlabel", "Capacity (Ah)");
    model.result("pg182").set("xlabelactive", true);
    model.result("pg182").set("ylabel", "Voltage (V)");
    model.result("pg182").set("ylabelactive", true);
    model.result("pg182").set("axislimits", true);
    model.result("pg182").set("xmin", -0.049841843427016114);
    model.result("pg182").set("xmax", 5.40389419922661);
    model.result("pg182").set("ymin", 2.495880550455565);
    model.result("pg182").set("ymax", 3.669414872287648);
    model.result("pg182").set("manualgrid", true);
    model.result("pg182").set("xspacing", ".5");
    model.result("pg182").set("yspacing", ".2");
    model.result("pg182").set("legendpos", "middleright");
    model.result("pg182").set("smooth", "internal");
    model.result("pg182").feature("tblp1").label("0.5PC");
    model.result("pg182").feature("tblp1").set("table", "tbl22");
    model.result("pg182").feature("tblp1").set("xaxisdata", 1);
    model.result("pg182").feature("tblp1").set("plotcolumninput", "manual");
    model.result("pg182").feature("tblp1").set("linewidth", 3);
    model.result("pg182").feature("tblp1").set("linewidthslider", 3);
    model.result("pg182").feature("tblp2").active(false);
    model.result("pg182").feature("tblp2").label("0.5PD");
    model.result("pg182").feature("tblp2").set("table", "tbl22");
    model.result("pg182").feature("tblp2").set("xaxisdata", 3);
    model.result("pg182").feature("tblp2").set("plotcolumninput", "manual");
    model.result("pg182").feature("tblp2").set("linecolor", "cyclereset");
    model.result("pg182").feature("tblp3").label("1PC");
    model.result("pg182").feature("tblp3").set("table", "tbl22");
    model.result("pg182").feature("tblp3").set("xaxisdata", 5);
    model.result("pg182").feature("tblp3").set("plotcolumninput", "manual");
    model.result("pg182").feature("tblp3").set("linewidth", 3);
    model.result("pg182").feature("tblp3").set("linewidthslider", 3);
    model.result("pg182").feature("tblp4").active(false);
    model.result("pg182").feature("tblp4").label("1PD");
    model.result("pg182").feature("tblp4").set("table", "tbl22");
    model.result("pg182").feature("tblp4").set("xaxisdata", 7);
    model.result("pg182").feature("tblp4").set("plotcolumninput", "manual");
    model.result("pg182").feature("tblp5").label("2PC");
    model.result("pg182").feature("tblp5").set("table", "tbl22");
    model.result("pg182").feature("tblp5").set("xaxisdata", 9);
    model.result("pg182").feature("tblp5").set("plotcolumninput", "manual");
    model.result("pg182").feature("tblp5").set("linewidth", 3);
    model.result("pg182").feature("tblp5").set("linewidthslider", 3);
    model.result("pg182").feature("tblp6").active(false);
    model.result("pg182").feature("tblp6").label("2PD");
    model.result("pg182").feature("tblp6").set("table", "tbl22");
    model.result("pg182").feature("tblp6").set("xaxisdata", 11);
    model.result("pg182").feature("tblp6").set("plotcolumninput", "manual");
    model.result("pg182").feature("glob1").set("looplevelinput", new String[]{"all", "all", "manual"});
    model.result("pg182").feature("glob1").set("descr", new String[]{"\u70b9\u63a2\u9488 1"});
    model.result("pg182").feature("glob1").set("xdata", "expr");
    model.result("pg182").feature("glob1").set("xdataexpr", "comp1.Q1");
    model.result("pg182").feature("glob1").set("xdataunit", "Ah");
    model.result("pg182").feature("glob1").set("linewidth", "preference");
    model.result("pg182").feature("glob2").set("looplevelinput", new String[]{"all", "all", "manual"});
    model.result("pg182").feature("glob2").set("looplevel", new String[]{"", "1, 2, 3", "2"});
    model.result("pg182").feature("glob2").set("descr", new String[]{"\u70b9\u63a2\u9488 1"});
    model.result("pg182").feature("glob2").set("xdata", "expr");
    model.result("pg182").feature("glob2").set("xdataexpr", "comp1.Q1");
    model.result("pg182").feature("glob2").set("xdataunit", "Ah");
    model.result("pg182").feature("glob2").set("linewidth", "preference");
    model.result("pg184").label("\u8f6f\u53050.5~2P\u5145\u653e 2");
    model.result("pg184").set("data", "none");
    model.result("pg184").set("xlabel", "\u5217 1");
    model.result("pg184").set("smooth", "internal");
    model.result("pg184").set("xlabelactive", false);
    model.result("pg184").feature("tblp1").active(false);
    model.result("pg184").feature("tblp1").label("0.5PC");
    model.result("pg184").feature("tblp1").set("table", "tbl22");
    model.result("pg184").feature("tblp1").set("xaxisdata", 1);
    model.result("pg184").feature("tblp1").set("plotcolumninput", "manual");
    model.result("pg184").feature("tblp3").active(false);
    model.result("pg184").feature("tblp3").label("1PC");
    model.result("pg184").feature("tblp3").set("table", "tbl22");
    model.result("pg184").feature("tblp3").set("plotcolumninput", "manual");
    model.result("pg184").feature("tblp5").active(false);
    model.result("pg184").feature("tblp5").label("2PC");
    model.result("pg184").feature("tblp5").set("table", "tbl22");
    model.result("pg184").feature("tblp5").set("plotcolumninput", "manual");
    model.result("pg184").feature("tblp2").label("0.5PD");
    model.result("pg184").feature("tblp2").set("table", "tbl22");
    model.result("pg184").feature("tblp2").set("plotcolumninput", "manual");
    model.result("pg184").feature("tblp2").set("linecolor", "cyclereset");
    model.result("pg184").feature("tblp4").label("1PD");
    model.result("pg184").feature("tblp4").set("table", "tbl22");
    model.result("pg184").feature("tblp4").set("plotcolumninput", "manual");
    model.result("pg184").feature("tblp6").label("2PD");
    model.result("pg184").feature("tblp6").set("table", "tbl22");
    model.result("pg184").feature("tblp6").set("plotcolumninput", "manual");
    model.result("pg183").label("\u8f6f\u53055~25\u2103\u5145\u653e");
    model.result("pg183").set("data", "none");
    model.result("pg183").set("smooth", "internal");
    model.result("pg183").feature("glob3").active(false);
    model.result("pg183").feature("glob3")
         .set("descr", new String[]{"\u7535\u538b\u8868 # \u4e24\u7aef\u7684\u7535\u538b", ""});
    model.result("pg183").feature("glob3").set("xdatasolnumtype", "all");
    model.result("pg183").feature("glob3").set("xdata", "expr");
    model.result("pg183").feature("glob3").set("xdataexpr", "comp1.Q2+2.913[Ah]");
    model.result("pg183").feature("glob3").set("xdataunit", "");
    model.result("pg183").feature("glob3").set("xdatadescr", "comp1.Q2+2.913[Ah]");
    model.result("pg183").feature("glob3").set("linestyle", "dashed");
    model.result("pg183").feature("glob3").set("linecolor", "cyclereset");
    model.result("pg183").feature("glob3").set("linewidth", 2);
    model.result("pg183").feature("glob3").set("linewidthslider", 2);
    model.result("pg183").feature("glob3").set("linemarker", "diamond");
    model.result("pg186").label("\u63a2\u9488\u7ed8\u56fe\u7ec4 186");
    model.result("pg186").set("data", "none");
    model.result("pg186").set("xlabel", "\u65f6\u95f4 (s)");
    model.result("pg186").set("smooth", "internal");
    model.result("pg186").set("window", "window10");
    model.result("pg186").set("windowtitle", "\u63a2\u9488\u56fe\u201c10\u201d");
    model.result("pg186").set("xlabelactive", false);
    model.result("pg186").create("tblp1", "Table");
    model.result("pg186").feature("tblp1").label("\u63a2\u9488\u8868\u56fe 1");
    model.result("pg186").feature("tblp1").set("plotcolumninput", "manual");
    model.result("pg186").feature("tblp1").set("legend", true);
    model.result("pg187").label("Resistance decomposition - by location");
    model.result("pg187").set("looplevelinput", new String[]{"all", "manual", "manual"});
    model.result("pg187").set("looplevel", new String[]{"", "2", "1"});
    model.result("pg187").set("titletype", "manual");
    model.result("pg187").set("title", "Resistance decomposition by location-CW391");
    model.result("pg187").set("xlabel", "Time (s)");
    model.result("pg187").set("xlabelactive", true);
    model.result("pg187").set("ylabel", "Resistance (m\u03a9)");
    model.result("pg187").set("ylabelactive", true);
    model.result("pg187").set("axislimits", true);
    model.result("pg187").set("xmin", -189.0502049150137);
    model.result("pg187").set("xmax", 17229.03791098396);
    model.result("pg187").set("ymin", -39.31722519188834);
    model.result("pg187").set("ymax", 0.12839069364331723);
    model.result("pg187").set("manualgrid", true);
    model.result("pg187").set("xspacing", 2000);
    model.result("pg187").set("yspacing", 10);
    model.result("pg187").set("legendpos", "lowermiddle");
    model.result("pg187").feature("glob1").label("Resistance decomposition - by location");
    model.result("pg187").feature("glob1").set("unit", new String[]{"m\u03a9"});
    model.result("pg187").feature("glob1").set("descr", new String[]{""});
    model.result("pg187").feature("glob1").set("linewidth", 4);
    model.result("pg187").feature("glob1").set("linewidthslider", 4);
    model.result("pg187").feature("glob1").set("legendmethod", "manual");
    model.result("pg187").feature("glob1").set("legends", new String[]{"Total", "CW511"});
    model.result("pg187").feature("glob2").label("Resistance decomposition - by location 1");
    model.result("pg187").feature("glob2").set("unit", new String[]{"m\u03a9", "m\u03a9", "m\u03a9"});
    model.result("pg187").feature("glob2").set("descr", new String[]{"V", "V", "V"});
    model.result("pg187").feature("glob2").set("linestyle", "dashed");
    model.result("pg187").feature("glob2").set("linewidth", 4);
    model.result("pg187").feature("glob2").set("linewidthslider", 4);
    model.result("pg187").feature("glob2").set("legendmethod", "manual");
    model.result("pg187").feature("glob2").set("legends", new String[]{"total_neg", "total_pos", "total_sep"});
    model.result("pg188").label("Resistance decomposition - by type");
    model.result("pg188").set("looplevelinput", new String[]{"all", "manual", "manual"});
    model.result("pg188").set("looplevel", new String[]{"", "2", "1"});
    model.result("pg188").set("titletype", "manual");
    model.result("pg188").set("title", "Resistance decomposition - by type");
    model.result("pg188").set("xlabel", "Time (s)");
    model.result("pg188").set("xlabelactive", true);
    model.result("pg188").set("ylabel", "Resistance (m\u03a9)");
    model.result("pg188").set("ylabelactive", true);
    model.result("pg188").set("axislimits", true);
    model.result("pg188").set("xmin", 820.4111429094924);

    return model;
  }

  public static Model run15(Model model) {
    model.result("pg188").set("xmax", 13501.933927504217);
    model.result("pg188").set("ymin", -4.041945757437372);
    model.result("pg188").set("ymax", 55.483015351015986);
    model.result("pg188").set("manualgrid", true);
    model.result("pg188").set("xspacing", 2000);
    model.result("pg188").set("yspacing", 10);
    model.result("pg188").set("legendpos", "uppermiddle");
    model.result("pg188").feature("glob1").label("Resistance decomposition - by location");
    model.result("pg188").feature("glob1").set("unit", new String[]{"m\u03a9"});
    model.result("pg188").feature("glob1").set("descr", new String[]{""});
    model.result("pg188").feature("glob1").set("linewidth", 4);
    model.result("pg188").feature("glob1").set("linewidthslider", 4);
    model.result("pg188").feature("glob1").set("legendmethod", "manual");
    model.result("pg188").feature("glob1").set("legends", new String[]{"\u603b"});
    model.result("pg188").feature("glob2").label("Resistance decomposition - by location 1");
    model.result("pg188").feature("glob2")
         .set("unit", new String[]{"m\u03a9", "m\u03a9", "m\u03a9", "m\u03a9", "m\u03a9"});
    model.result("pg188").feature("glob2").set("descr", new String[]{"V", "V", "V", "V", "V"});
    model.result("pg188").feature("glob2").set("linestyle", "dashed");
    model.result("pg188").feature("glob2").set("linewidth", 4);
    model.result("pg188").feature("glob2").set("linewidthslider", 4);
    model.result("pg188").feature("glob2").set("legendmethod", "manual");
    model.result("pg188").feature("glob2").set("legends", new String[]{"ohms", "ohml", "dl", "ds", "RCT"});
    model.result("pg188").feature("ptgr1").active(false);
    model.result("pg188").feature("ptgr1").set("plotonsecyaxis", true);
    model.result("pg188").feature("ptgr1").set("linewidth", 3);
    model.result("pg188").feature("ptgr1").set("linewidthslider", 3);
    model.result().export("img1").set("size", "presentation");
    model.result().export("img1").set("unit", "px");
    model.result().export("img1").set("lockratio", "off");
    model.result().export("img1").set("width", "874");
    model.result().export("img1").set("height", "656");
    model.result().export("img1").set("resolution", "96");
    model.result().export("img1").set("zoomextents", "off");
    model.result().export("img1").set("antialias", "on");
    model.result().export("img1").set("options1d", "on");
    model.result().export("img1").set("options2d", "off");
    model.result().export("img1").set("options3d", "off");
    model.result().export("img1").set("title1d", "on");
    model.result().export("img1").set("title2d", "on");
    model.result().export("img1").set("title3d", "on");
    model.result().export("img1").set("legend1d", "on");
    model.result().export("img1").set("legend2d", "on");
    model.result().export("img1").set("legend3d", "on");
    model.result().export("img1").set("axes1d", "on");
    model.result().export("img1").set("axes2d", "on");
    model.result().export("img1").set("logo1d", "on");
    model.result().export("img1").set("logo2d", "on");
    model.result().export("img1").set("logo3d", "on");
    model.result().export("img1").set("showgrid", "on");
    model.result().export("img1").set("axisorientation", "on");
    model.result().export("img1").set("grid", "on");
    model.result().export("img1").set("fontsize", "12");
    model.result().export("img1").set("colortheme", "globaltheme");
    model.result().export("img1").set("background", "transparent");
    model.result().export("img1").set("gltfincludelines", "on");
    model.result().export("img1").set("qualitylevel", "92");
    model.result().export("img1").set("qualityactive", "off");
    model.result().export("img1").set("imagetype", "png");
    model.result().export("img1").set("target", "linked");
    model.result().export("img1").set("addsuffix", "off");
    model.result().export("img1").set("lockview", "off");
    model.result().export("img1").set("highprecisioncolor", "off");
    model.result().export("img1").set("customcolor", new double[]{1, 1, 1});
    model.result().export("img1").set("width", 800);
    model.result().export("img1").set("height", 600);
    model.result().export("img1").set("resolution", 96);
    model.result().export("img1").set("sizedesc", "212 x 159 mm");
    model.result().export("img1").set("fontsize", 12);
    model.result().export("img1").set("background", "current");
    model.result().export("img1").set("target", "file");
    model.result().export("img1").set("logo1d", false);
    model.result().export("img1").set("size", "presentation");
    model.result().export("img1").set("unit", "px");
    model.result().export("img1").set("height", "600");
    model.result().export("img1").set("width", "800");
    model.result().export("img1").set("lockratio", "off");
    model.result().export("img1").set("resolution", "96");
    model.result().export("img1").set("antialias", "on");
    model.result().export("img1").set("zoomextents", "off");
    model.result().export("img1").set("fontsize", "12");
    model.result().export("img1").set("colortheme", "globaltheme");
    model.result().export("img1").set("customcolor", new double[]{1, 1, 1});
    model.result().export("img1").set("background", "current");
    model.result().export("img1").set("gltfincludelines", "on");
    model.result().export("img1").set("title1d", "on");
    model.result().export("img1").set("legend1d", "on");
    model.result().export("img1").set("logo1d", "off");
    model.result().export("img1").set("options1d", "on");
    model.result().export("img1").set("title2d", "on");
    model.result().export("img1").set("legend2d", "on");
    model.result().export("img1").set("logo2d", "on");
    model.result().export("img1").set("options2d", "off");
    model.result().export("img1").set("title3d", "on");
    model.result().export("img1").set("legend3d", "on");
    model.result().export("img1").set("logo3d", "on");
    model.result().export("img1").set("options3d", "off");
    model.result().export("img1").set("axisorientation", "on");
    model.result().export("img1").set("grid", "on");
    model.result().export("img1").set("axes1d", "on");
    model.result().export("img1").set("axes2d", "on");
    model.result().export("img1").set("showgrid", "on");
    model.result().export("img1").set("target", "file");
    model.result().export("img1").set("qualitylevel", "92");
    model.result().export("img1").set("qualityactive", "off");
    model.result().export("img1").set("imagetype", "png");
    model.result().export("img1").set("lockview", "off");
    model.result().export("img1").set("highprecisioncolor", "off");
    model.result().export("img1").set("size", "presentation");
    model.result().export("img1").set("unit", "px");
    model.result().export("img1").set("height", "600");
    model.result().export("img1").set("width", "800");
    model.result().export("img1").set("lockratio", "off");
    model.result().export("img1").set("resolution", "96");
    model.result().export("img1").set("antialias", "on");
    model.result().export("img1").set("zoomextents", "off");
    model.result().export("img1").set("fontsize", "12");
    model.result().export("img1").set("colortheme", "globaltheme");
    model.result().export("img1").set("customcolor", new double[]{1, 1, 1});
    model.result().export("img1").set("background", "current");
    model.result().export("img1").set("gltfincludelines", "on");
    model.result().export("img1").set("title1d", "on");
    model.result().export("img1").set("legend1d", "on");
    model.result().export("img1").set("logo1d", "off");
    model.result().export("img1").set("options1d", "on");
    model.result().export("img1").set("title2d", "on");
    model.result().export("img1").set("legend2d", "on");
    model.result().export("img1").set("logo2d", "on");
    model.result().export("img1").set("options2d", "off");
    model.result().export("img1").set("title3d", "on");
    model.result().export("img1").set("legend3d", "on");
    model.result().export("img1").set("logo3d", "on");
    model.result().export("img1").set("options3d", "off");
    model.result().export("img1").set("axisorientation", "on");
    model.result().export("img1").set("grid", "on");
    model.result().export("img1").set("axes1d", "on");
    model.result().export("img1").set("axes2d", "on");
    model.result().export("img1").set("showgrid", "on");
    model.result().export("img1").set("target", "file");
    model.result().export("img1").set("qualitylevel", "92");
    model.result().export("img1").set("qualityactive", "off");
    model.result().export("img1").set("imagetype", "png");
    model.result().export("img1").set("lockview", "off");
    model.result().export("img1").set("highprecisioncolor", "off");
    model.result().export("img1").set("size", "presentation");
    model.result().export("img1").set("unit", "px");
    model.result().export("img1").set("height", "600");
    model.result().export("img1").set("width", "800");
    model.result().export("img1").set("lockratio", "off");
    model.result().export("img1").set("resolution", "96");
    model.result().export("img1").set("antialias", "on");
    model.result().export("img1").set("zoomextents", "off");
    model.result().export("img1").set("fontsize", "12");
    model.result().export("img1").set("colortheme", "globaltheme");
    model.result().export("img1").set("customcolor", new double[]{1, 1, 1});
    model.result().export("img1").set("background", "current");
    model.result().export("img1").set("gltfincludelines", "on");
    model.result().export("img1").set("title1d", "on");
    model.result().export("img1").set("legend1d", "on");
    model.result().export("img1").set("logo1d", "off");
    model.result().export("img1").set("options1d", "on");
    model.result().export("img1").set("title2d", "on");
    model.result().export("img1").set("legend2d", "on");
    model.result().export("img1").set("logo2d", "on");
    model.result().export("img1").set("options2d", "off");
    model.result().export("img1").set("title3d", "on");
    model.result().export("img1").set("legend3d", "on");
    model.result().export("img1").set("logo3d", "on");
    model.result().export("img1").set("options3d", "off");
    model.result().export("img1").set("axisorientation", "on");
    model.result().export("img1").set("grid", "on");
    model.result().export("img1").set("axes1d", "on");
    model.result().export("img1").set("axes2d", "on");
    model.result().export("img1").set("showgrid", "on");
    model.result().export("img1").set("target", "file");
    model.result().export("img1").set("qualitylevel", "92");
    model.result().export("img1").set("qualityactive", "off");
    model.result().export("img1").set("imagetype", "png");
    model.result().export("img1").set("lockview", "off");
    model.result().export("img1").set("highprecisioncolor", "off");

    model.nodeGroup("grp1").label("\u7b97\u5b50");
    model.nodeGroup("grp1").add("func", "step2");
    model.nodeGroup("grp1").add("func", "rect2");
    model.nodeGroup("grp1").add("func", "gp1");
    model.nodeGroup("grp1").add("cpl", "intop1");
    model.nodeGroup("grp1").add("cpl", "intop2");
    model.nodeGroup("grp1").add("cpl", "intop3");
    model.nodeGroup("grp1").add("cpl", "intop4");
    model.nodeGroup("grp1").add("cpl", "intop5");
    model.nodeGroup("grp1").add("cpl", "aveop1");
    model.nodeGroup("grp1").add("cpl", "aveop2");
    model.nodeGroup("grp1").add("cpl", "aveop3");
    model.nodeGroup("grp1").add("cpl", "aveop4");
    model.nodeGroup("grp1").add("cpl", "aveop5");
    model.nodeGroup("grp1").add("cpl", "intop6");

    return model;
  }


  private static String[][] loadTableFromSnapshot(String methodName, String functionTag) {
    try {
      java.nio.file.Path location = java.nio.file.Paths.get(
          hithium_314pouch1D.class.getProtectionDomain().getCodeSource().getLocation().toURI());
      java.nio.file.Path baseDirectory = java.nio.file.Files.isDirectory(location)
          ? location
          : location.getParent();
      String source = java.nio.file.Files.readString(
          baseDirectory.resolve("hithium_314pouch1D.snapshot.txt"),
          java.nio.charset.StandardCharsets.UTF_8);

      String methodMarker = "  public static Model " + methodName + "(Model model) {";
      int methodStart = source.indexOf(methodMarker);
      if (methodStart < 0) {
        throw new IllegalStateException("Method not found in snapshot: " + methodName);
      }

      int methodEnd = source.indexOf("\n  public static Model ", methodStart + methodMarker.length());
      int mainStart = source.indexOf("\n  public static void main", methodStart + methodMarker.length());
      if (methodEnd < 0 || (mainStart >= 0 && mainStart < methodEnd)) {
        methodEnd = mainStart;
      }
      if (methodEnd < 0) {
        throw new IllegalStateException("Method boundary not found in snapshot: " + methodName);
      }

      String methodBlock = source.substring(methodStart, methodEnd);
      String functionMarker = ".func(\"" + functionTag + "\")";
      int functionStart = methodBlock.indexOf(functionMarker);
      if (functionStart < 0) {
        throw new IllegalStateException("Function tag not found in snapshot: " + functionTag);
      }

      String tableMarker = ".set(\"table\", new String[][]{";
      int tableStart = methodBlock.indexOf(tableMarker, functionStart);
      if (tableStart < 0) {
        throw new IllegalStateException("Table literal not found in snapshot for: " + functionTag);
      }
      tableStart += tableMarker.length();

      int braceDepth = 1;
      int cursor = tableStart;
      while (cursor < methodBlock.length() && braceDepth > 0) {
        char ch = methodBlock.charAt(cursor);
        if (ch == '{') {
          braceDepth++;
        } else if (ch == '}') {
          braceDepth--;
        }
        cursor++;
      }
      if (braceDepth != 0) {
        throw new IllegalStateException("Unbalanced table literal in snapshot for: " + functionTag);
      }

               String tableBlock = methodBlock.substring(tableStart, cursor - 1);
               java.util.ArrayList<String[]> rows = new java.util.ArrayList<>();
               for (String line : tableBlock.split("\\R")) {
                    String trimmed = line.trim();
                    if (!trimmed.startsWith("{\"")) {
                         continue;
                    }
                    if (trimmed.endsWith(",")) {
                         trimmed = trimmed.substring(0, trimmed.length() - 1);
                    }
                    if (!trimmed.endsWith("\"}")) {
                         throw new IllegalStateException("Unrecognized table row: " + trimmed);
                    }
                    String content = trimmed.substring(2, trimmed.length() - 2);
                    String separator = "\", \"";
                    int separatorIndex = content.indexOf(separator);
                    if (separatorIndex < 0) {
                         throw new IllegalStateException("Unrecognized table row: " + trimmed);
                    }
                    rows.add(new String[]{
                              content.substring(0, separatorIndex),
                              content.substring(separatorIndex + separator.length())
                    });
               }
      return rows.toArray(new String[0][]);
    } catch (Exception ex) {
      throw new IllegalStateException(
          "Unable to load snapshot table for " + methodName + "/" + functionTag, ex);
    }
  }

  public static void main(String[] args) {
    Model model = run();
    model = run2(model);
    model = run3(model);
    model = run4(model);
    model = run5(model);
    model = run6(model);
    model = run7(model);
    model = run8(model);
    model = run9(model);
    model = run10(model);
    model = run11(model);
    model = run12(model);
    model = run13(model);
    model = run14(model);
    run15(model);
  }

}

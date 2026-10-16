import com.comsol.model.*;
import com.comsol.model.util.*;
import java.util.*;

/** One-point solve of the actual saved 6.3 model; main sweep stays at 505 cases. */
public class SmokeTestNumber37 {
  private static final String PROJECT_ROOT = "D:/projects/number37-angle-sweep";
  public static Model run() throws Exception {
    Model model=ModelUtil.load("Smoke37",PROJECT_ROOT+"/models/NUMBER37_COMSOL63_angle_wavelength.mph");
    for(String tag:new String[]{"size","size1","size2"}) {
      System.out.println("MESH "+tag+" hmax="+model.component("comp1").mesh("mesh3").feature(tag).getString("hmax")
        +" custom="+model.component("comp1").mesh("mesh3").feature(tag).getString("custom"));
      if(!"size".equals(tag)) System.out.println("HMAXACTIVE "+tag+"="+model.component("comp1").mesh("mesh3").feature(tag).getString("hmaxactive"));
    }
    model.param().set("theta_inc","1[deg]");
    model.param().set("lambda0","1470[nm]");
    model.study().create("std_smoke");
    model.study("std_smoke").create("freq","Frequency");
    model.study("std_smoke").feature("freq").set("plist","c_const/lambda0");
    model.study("std_smoke").createAutoSequences("all");
    String smokeSol=null;
    for(String tag:model.sol().tags()) {
      if("std_smoke".equals(model.sol(tag).study()) && Arrays.asList(model.sol(tag).feature().tags()).contains("s1")) {
        smokeSol=tag;
      }
    }
    if(smokeSol==null) throw new IllegalStateException("No smoke-test solver");
    model.sol(smokeSol).feature("s1").feature("i1").active(true);
    model.sol(smokeSol).feature("s1").feature("i1").set("itrestart",300);
    model.sol(smokeSol).feature("s1").feature("fc1").set("linsolver","i1");
    model.sol(smokeSol).runAll();
    model.result().table().create("tblsmoke","Table");
    model.result().numerical().create("gevsmoke","EvalGlobal");
    String dataTag=null;
    for(String tag:model.result().dataset().tags()) {
      if("Solution".equals(model.result().dataset(tag).getType()) && smokeSol.equals(model.result().dataset(tag).getString("solution"))) dataTag=tag;
    }
    if(dataTag==null) throw new IllegalStateException("No smoke-test solution dataset");
    model.result().numerical("gevsmoke").set("data",dataTag);
    model.result().numerical("gevsmoke").set("expr",new String[]{"theta_inc/1[deg]","lambda0/1[nm]","ewfd.Rport_1","ewfd.Tport_2","ewfd.Rtotal","ewfd.Ttotal","ewfd.RTtotal","ewfd.Atotal"});
    model.result().numerical("gevsmoke").set("table","tblsmoke");
    model.result().numerical("gevsmoke").setResult();
    double[][] rt=model.result().numerical("gevsmoke").getReal();
    for(double[] row:rt) for(double v:row) if(Double.isNaN(v)||Double.isInfinite(v)) throw new IllegalStateException("Nonfinite result");
    System.out.println("SMOKE_RESULT="+Arrays.deepToString(rt));
    model.result().table("tblsmoke").save(PROJECT_ROOT+"/validation/smoke-rt.csv");
    model.save(PROJECT_ROOT+"/work/NUMBER37_smoke_solved.mph");
    System.out.println("NUMBER37_SMOKE_OK");
    return model;
  }
  public static void main(String[] args) throws Exception {run();}
}

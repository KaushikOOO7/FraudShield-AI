import com.intellij.openapi.Disposable;
import com.intellij.openapi.util.Disposer;
import com.intellij.psi.PsiErrorElement;
import com.intellij.psi.util.PsiTreeUtil;
import org.jetbrains.kotlin.cli.jvm.compiler.EnvironmentConfigFiles;
import org.jetbrains.kotlin.cli.jvm.compiler.KotlinCoreEnvironment;
import org.jetbrains.kotlin.config.CompilerConfiguration;
import org.jetbrains.kotlin.psi.KtPsiFactory;
import java.nio.file.Files;
import java.nio.file.Path;

/** IDE-parser syntax check only: does not resolve dependencies or replace the pinned Gradle build. */
public final class KotlinSyntaxAudit {
    public static void main(String[] args) throws Exception {
        Disposable disposable = Disposer.newDisposable();
        int errors = 0;
        int count = 0;
        try {
            var environment = KotlinCoreEnvironment.createForProduction(disposable, new CompilerConfiguration(), EnvironmentConfigFiles.JVM_CONFIG_FILES);
            var factory = new KtPsiFactory(environment.getProject(), false);
            try (var files = Files.walk(Path.of("app/src"))) {
                for (Path path : files.filter(p -> p.toString().endsWith(".kt")).toList()) {
                    var text = Files.readString(path);
                    var file = factory.createFile(path.getFileName().toString(), text);
                    count++;
                    for (var error : PsiTreeUtil.findChildrenOfType(file, PsiErrorElement.class)) {
                        System.out.println(path + ": " + error.getErrorDescription());
                        errors++;
                    }
                }
            }
        } finally { Disposer.dispose(disposable); }
        System.out.println("Kotlin IDE syntax audit: " + count + " files, " + errors + " parse errors. No typechecking, Gradle build or Android execution.");
        if (errors != 0) System.exit(1);
    }
}

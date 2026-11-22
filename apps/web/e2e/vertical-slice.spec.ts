import { expect, test } from "@playwright/test";

test("registro, lección con micrófono sintético y progreso", async ({ page }) => {
  const email = `e2e-${Date.now()}@example.com`;

  await page.goto("/login");
  await page.getByRole("link", { name: "Regístrate" }).click();
  await expect(page.getByRole("heading", { name: "Crea tu cuenta" })).toBeVisible();

  await page.getByLabel("Nombre").fill("Alumno E2E");
  await page.getByLabel("Correo").fill(email);
  await page.getByLabel("Contraseña").fill("secreto123");
  await page.getByRole("button", { name: "Crear cuenta" }).click();

  await expect(page.getByRole("heading", { name: "Tu curso de inglés" })).toBeVisible();
  await page.getByRole("link", { name: /1\. Saludos/ }).click();
  await expect(page.getByRole("heading", { name: "Saludos" })).toBeVisible();

  // TTS de referencia y grabación con el micrófono falso de Chromium.
  await page.getByRole("button", { name: /Escuchar/ }).first().click();
  await page.getByRole("button", { name: /Grabar/ }).click();
  await page.getByRole("button", { name: "Acepto y grabo" }).click();
  await expect(page.getByRole("button", { name: /Detener/ })).toBeVisible();
  await page.waitForTimeout(1800);
  await page.getByRole("button", { name: /Detener/ }).click();
  await expect(page.getByText("Intento guardado")).toBeVisible({ timeout: 30_000 });
  await expect(page.locator("audio").first()).toBeVisible();

  // Opción múltiple.
  await page.getByRole("radio", { name: "Good morning" }).check();
  await page.getByRole("button", { name: "Comprobar" }).first().click();
  await expect(page.getByText("¡Muy bien!").first()).toBeVisible();

  // Traducción.
  await page.getByPlaceholder("Escribe tu respuesta en inglés").fill("How are you?");
  await page.getByRole("button", { name: "Comprobar" }).nth(1).click();
  await expect(page.getByText("¡Muy bien!").nth(1)).toBeVisible();

  const complete = page.getByRole("button", { name: "Completar lección" });
  await expect(complete).toBeEnabled();
  await complete.click();

  await expect(page.getByRole("heading", { name: "Tu progreso" })).toBeVisible();
  await expect(page.getByText("1 / 10").first()).toBeVisible();
  await expect(
    page.locator(".stat").filter({ hasText: "Intentos registrados" }).getByText("3", { exact: true }),
  ).toBeVisible();
});

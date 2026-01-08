# Kit de Design AtivaBank 🎨

Este kit contém os arquivos essenciais para replicar a interface moderna do AtivaBank em outros projetos React.

## Conteúdo do Kit

1.  **styles.css**: O "coração" do design. Contém todas as variáveis de cor (CSS Variables), reset de layout e classes utilitárias (.card, .btn, .input-premium).
2.  **components.tsx**: Componentes base (Card, Button, Modal, InfoBox) prontos para copiar e colar.
3.  **layout_example.tsx**: Exemplo de como montar a **Sidebar** (Menu Lateral) com a área de conteúdo principal.

## Como Usar

1.  Copie o arquivo `styles.css` para a pasta `src` do seu novo projeto e importe-o no seu arquivo principal (ex: `main.tsx` ou `App.tsx`):
    ```javascript
    import './styles.css';
    ```

2.  Copie os componentes de `components.tsx` para sua biblioteca de componentes. Eles dependem apenas do React e das classes do `styles.css`.

3.  Use a estrutura do `layout_example.tsx` para criar seu layout principal. Lembre-se de instalar os ícones se quiser usar os mesmos (`lucide-react`):
    ```bash
    npm install lucide-react
    ```

## Dicas de Customização

- Para mudar a cor principal, edite a variável `--primary` no topo do `styles.css`.
- Para ajustar o arredondamento, mude `--border-radius`.

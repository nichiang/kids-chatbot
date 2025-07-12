// Character Image Configuration
// Edit this file to easily swap character images without touching the main code

const CHARACTER_CONFIG = {
    bear: {
        'theme-space': '../design/characterSheets/bearSpaceHead.PNG',
        'theme-fantasy': '../design/characterSheets/bearMagicHead.PNG',
        'theme-sports': '../design/characterSheets/bearSportsHead.PNG',
        'theme-food': '../design/characterSheets/bearCookingHead.PNG',
        'theme-creative': '../design/characterSheets/bearArtHead.PNG',
        'theme-whimsical': '../design/characterSheets/bearMagicHead.PNG', // Use magic for whimsical
        'theme-ocean': '../design/characterSheets/bearOceanHead.PNG', // Now has specific ocean head
        'theme-animals': '../design/characterSheets/bearOceanHead.PNG', // Use ocean for animals/nature
        'theme-elegant': '../design/characterSheets/bearFallbackHead.png', // Use fallback for professional
        'theme-fun': '../design/characterSheets/bearSpaceHead.PNG', // Use space for fun
        'fallback': '../design/characterSheets/bearFallbackHead.png'
    },
    boy: {
        'theme-space': '../design/characterSheets/boySpaceHead.png',
        'theme-sports': '../design/characterSheets/boySportsHead.png', 
        'theme-ocean': '../design/characterSheets/boyOceanHead.png',
        'theme-animals': '../design/characterSheets/boyOceanHead.png', // Use ocean for animals/nature
        'theme-fantasy': '../design/characterSheets/boyDefault.png', // No specific fantasy head yet
        'theme-whimsical': '../design/characterSheets/boyDefault.png', // No specific whimsical head yet
        'theme-food': '../design/characterSheets/boyDefault.png', // No specific food head yet
        'theme-creative': '../design/characterSheets/boyDefault.png', // No specific creative head yet
        'theme-elegant': '../design/characterSheets/boyDefault.png', // No specific elegant head yet
        'theme-fun': '../design/characterSheets/boySpaceHead.png', // Use space for fun
        'fallback': '../design/characterSheets/boyDefault.png'
    }
};

// Easy function to get character image path
function getCharacterImage(characterType, theme) {
    const config = CHARACTER_CONFIG[characterType];
    if (!config) return CHARACTER_CONFIG.boy.fallback; // Default fallback
    
    return config[theme] || config.fallback || CHARACTER_CONFIG.boy.fallback;
}